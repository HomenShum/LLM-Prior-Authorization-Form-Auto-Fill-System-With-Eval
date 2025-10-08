# DevOps Engineering Project

Thank you for taking the time to complete our DevOps take‑home project. We appreciate your effort and want this to feel like a realistic slice of how we ship infra at **Develop Health**.

You’ll take the included **FastAPI** app from this repo and make it **production‑deployable on Google Kubernetes Engine (GKE)**, ideally via a **GitHub Actions** pipeline. Your goal is to leave us with a repository where we can read your docs, inspect the pipeline and infrastructure, and understand how we’d ship this app **safely and repeatably**.

> **Timebox:** \~3 hours for implementation. You may not finish everything—that’s okay. Favor high‑quality implementations, clear comments where helpful, and a short design write‑up on what you would do with more time over volume of code.

---

## Overview

You will:

* Containerize and ship the FastAPI app to **GKE** using **Artifact Registry**.
* (If time permits) Create a CI/CD flow that builds and deploys with **GitHub Actions**.


> If you cannot use GCP for any reason, you may fall back to **Kind/Minikube**. Please clearly document how the same workflow would target GKE (what would change and why). Preferred submissions deploy to **GKE Autopilot** using **OIDC / Workload Identity Federation** (no JSON key).

---

## Objective

Implement infrastructure and CI/CD so that:

* The app is built into a container image and **pushed to Artifact Registry**.
* The app is **deployed to GKE** and **reachable over the public internet** (via Service `LoadBalancer` or Ingress—you choose and justify).
* Deployments are **repeatable** and **documented**, with a small runbook for rollback and debugging.
* (If time permits) A **GitHub Actions** workflow handles build & deploy.

  * On PRs: tests and image build (no deploy).
  * On merges to protected branches (e.g., `staging`, `main`): build, push, deploy.


---

## Extras (optional)

Choose depth over breadth:

* **Environments:** staging + prod.
* **Autoscaling:** simple HPA (CPU‑based).
* **Security:** Trivy scan, disallow `:latest`, runAsNonRoot, readOnlyRootFilesystem.
* **Policy:** NetworkPolicy for namespace isolation.
* **Ingress + TLS:** Managed certs and DNS (document how you’d wire it).
* **Costs:** brief note on Autopilot vs Standard costs; cleanup steps.

---

## Time Commitment

* Implementation: **\~3 hours** (timebox).
* Design write‑up: **30–45 minutes**.

Partial solutions are welcome—just document what’s left and next steps.

---

## Deliverables

1. **A PR**:
   * Include all your changes in a new PR on this repo

2. A short **design write‑up** (`DESIGN.md` or README section) that covers:

   * Architecture diagram or textual description.
   * Design choices, assumptions, and trade‑offs (cluster mode, LB vs Ingress, IAM, etc.).
   * Security considerations (secrets, WIF, non‑root containers).
   * Reliability considerations (idempotency, rollback) and **next steps you’d take**.

3. A **Loom** (3–5 min) showing:

   * Deployment and how it runs
   * CI/CD if applicable
   * Quick overview of any code

---

## AI Tooling

Please use whatever helps you move quickly—Copilot, code assistants, etc. In your write‑up, include a brief overview of:

* What you used.
* Where it helped and where it didn’t.
* What you validated or changed after generation.

As with production code, **you** are responsible for the result. Be prepared to discuss any part of your solution.

---

We’re excited to see your approach and hear your reasoning in the write‑up and Loom.
