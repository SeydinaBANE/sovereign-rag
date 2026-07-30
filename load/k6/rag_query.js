import http from "k6/http";
import { check } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const API_KEY = __ENV.SRAG_API_KEY || "";

const headers = { "Content-Type": "application/json" };
if (API_KEY) {
  headers["X-API-Key"] = API_KEY;
}

export const options = {
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{endpoint:query}": ["p(95)<1000"],
  },
  scenarios: {
    ramp: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "20s", target: 10 },
        { duration: "40s", target: 50 },
        { duration: "20s", target: 0 },
      ],
      gracefulStop: "10s",
    },
  },
};

const QUESTIONS = [
  "How many days per week can employees work remotely?",
  "What is the data retention period for customer data?",
  "Does the remote work policy require manager approval?",
  "What happens to personal data under GDPR after retention?",
];

const CORPUS = [
  {
    id: "remote",
    text:
      "Acme Remote Work Policy. Employees may work remotely up to three days per " +
      "week with manager approval and a secure VPN connection.",
    source: "remote_work_policy.md",
  },
  {
    id: "retention",
    text:
      "Acme Data Retention Policy. Customer personal data is retained for a maximum " +
      "of twenty-four months and then permanently deleted under GDPR.",
    source: "data_retention_policy.md",
  },
];

export function setup() {
  const res = http.post(`${BASE_URL}/ingest`, JSON.stringify({ documents: CORPUS }), {
    headers,
  });
  check(res, { "corpus ingested": (r) => r.status === 200 });
}

export default function () {
  const question = QUESTIONS[Math.floor(Math.random() * QUESTIONS.length)];
  const res = http.post(`${BASE_URL}/query`, JSON.stringify({ text: question }), {
    headers,
    tags: { endpoint: "query" },
  });
  check(res, {
    "query 200": (r) => r.status === 200,
    "answer returned": (r) => r.status === 200 && r.json("refused") !== undefined,
  });
}
