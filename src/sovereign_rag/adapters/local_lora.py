from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sovereign_rag.domain.exceptions import FineTuningJobNotFound
from sovereign_rag.domain.models import (
    FineTuningJob,
    FineTuningSpec,
    FineTuningStatus,
    TrainingExample,
)


class LocalLoRAFineTuner:
    """On-premise LoRA/PEFT fine-tuning of an open-source LLM.

    Heavy dependencies (transformers/peft/trl/datasets) are imported lazily so the
    package stays importable without them. Trained adapters and a job registry are
    persisted under ``output_dir`` so data never leaves the cluster.
    """

    def __init__(self, output_dir: str) -> None:
        self._root = Path(output_dir)
        self._root.mkdir(parents=True, exist_ok=True)
        self._registry = self._root / "registry.json"

    def create_job(self, spec: FineTuningSpec) -> FineTuningJob:
        job_id = f"ftjob-local-{uuid4().hex[:12]}"
        adapter_dir = self._root / job_id
        job = FineTuningJob(
            id=job_id,
            base_model=spec.base_model,
            status=FineTuningStatus.RUNNING,
            tenant_id=spec.tenant_id,
            created_at=datetime.now(UTC).isoformat(),
            hyperparams=spec.hyperparams,
        )
        self._save(job)
        try:
            loss = self._train(spec, adapter_dir)
        except Exception as error:
            failed = job.model_copy(
                update={"status": FineTuningStatus.FAILED, "metrics": {"error": 1.0}}
            )
            self._save(failed)
            raise RuntimeError(f"Local LoRA training failed: {error}") from error
        succeeded = job.model_copy(
            update={
                "status": FineTuningStatus.SUCCEEDED,
                "fine_tuned_model": str(adapter_dir),
                "metrics": {"train_examples": float(len(spec.examples)), "train_loss": loss},
            }
        )
        self._save(succeeded)
        return succeeded

    def get_job(self, job_id: str) -> FineTuningJob:
        for job in self._load():
            if job.id == job_id:
                return job
        raise FineTuningJobNotFound(job_id)

    def list_jobs(self, tenant_id: str) -> list[FineTuningJob]:
        return [job for job in self._load() if job.tenant_id == tenant_id]

    def cancel_job(self, job_id: str) -> FineTuningJob:
        job = self.get_job(job_id)
        cancelled = job.model_copy(update={"status": FineTuningStatus.CANCELLED})
        self._save(cancelled)
        return cancelled

    def _train(self, spec: FineTuningSpec, adapter_dir: Path) -> float:
        from datasets import Dataset
        from peft import LoraConfig
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from trl import SFTConfig, SFTTrainer

        tokenizer = AutoTokenizer.from_pretrained(spec.base_model)  # nosec B615
        model = AutoModelForCausalLM.from_pretrained(spec.base_model)  # nosec B615
        rendered = [_render(example, tokenizer) for example in spec.examples]
        dataset = Dataset.from_dict({"text": rendered})
        trainer = SFTTrainer(
            model=model,
            train_dataset=dataset,
            peft_config=LoraConfig(task_type="CAUSAL_LM", r=16, lora_alpha=32, lora_dropout=0.05),
            args=SFTConfig(
                output_dir=str(adapter_dir),
                num_train_epochs=spec.hyperparams.epochs,
                learning_rate=spec.hyperparams.learning_rate,
                report_to=[],
            ),
        )
        result = trainer.train()
        trainer.save_model(str(adapter_dir))
        return float(getattr(result, "training_loss", 0.0))

    def _load(self) -> list[FineTuningJob]:
        if not self._registry.exists():
            return []
        return [
            FineTuningJob.model_validate_json(line)
            for line in self._registry.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _save(self, job: FineTuningJob) -> None:
        jobs = {item.id: item for item in self._load()}
        jobs[job.id] = job
        self._registry.write_text(
            "\n".join(item.model_dump_json() for item in jobs.values()) + "\n",
            encoding="utf-8",
        )


def _render(example: TrainingExample, tokenizer: object) -> str:
    apply = getattr(tokenizer, "apply_chat_template", None)
    messages = [message.model_dump() for message in example.messages]
    if callable(apply):
        return str(apply(messages, tokenize=False, add_generation_prompt=False))
    return "\n".join(f"{message.role}: {message.content}" for message in example.messages)
