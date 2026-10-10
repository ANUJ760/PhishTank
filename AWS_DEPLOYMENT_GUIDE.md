# GeCompose — AWS Deployment Guide

This guide covers deploying the GeCompose application on Amazon Web Services (AWS):
- **Backend**: Containerized FastAPI + OR-Tools solver via Docker.
- **Frontend**: High-performance React (Vite) Single Page Application (SPA).
- **Database**: PostgreSQL (Amazon RDS or Dockerized).

---

## 🏛️ Recommended Architecture Options

### Option A: The AWS Cloud-Native Best Practice (Recommended)
| Layer | AWS Service | Why | Cost |
|---|---|---|---|
| **Frontend** | **Amazon S3 + CloudFront** | Global edge CDN, ultra-fast TTFB, automatic free SSL | < $0.50/month (Free Tier) |
| **Backend** | **AWS App Runner** | Managed container service, automatic HTTPS, zero server admin, auto-scales | ~$5 – $15/month (pay per active request) |
| **Database** | **Amazon RDS PostgreSQL** (or Supabase/Neon) | Managed backups, multi-AZ, db.t4g.micro | Free Tier eligible for 12 months |

> **Single Domain Routing**: You can use CloudFront to route `/*` to your S3 bucket (Frontend) and `/api/*` to AWS App Runner (Backend). This eliminates all CORS issues and gives you a single clean domain name!

---

### Option B: The All-in-One EC2 Instance (Fastest & Simplest)
Run PostgreSQL, Backend, and Frontend all on a single AWS EC2 virtual machine using `docker-compose.prod.yml`.
- **Instance**: EC2 `t3.small` or `t3.medium` (Ubuntu 22.04 LTS).
- **Setup time**: ~5 minutes.
- **Command**: `docker compose -f docker-compose.prod.yml up -d --build`

---

## 🚀 Step-by-Step Instructions

---

### 📦 Guide 1: All-in-One EC2 Deployment (Easiest & Fastest)

#### Step 1: Launch an EC2 Instance
1. In the AWS Console, navigate to **EC2** → **Launch Instance**.
2. **Name**: `gecompose-server`
3. **AMI**: Ubuntu Server 22.04 LTS (64-bit x86).
4. **Instance type**: `t3.small` (2 vCPU, 2GB RAM) or `t3.medium` (4GB RAM).
5. **Key pair**: Create or select an existing `.pem` key pair.
6. **Security Group rules**:
   - Allow **SSH** (Port 22) from your IP.
   - Allow **HTTP** (Port 80) from `0.0.0.0/0`.
   - Allow **HTTPS** (Port 443) from `0.0.0.0/0`.
7. Click **Launch Instance**.

#### Step 2: Connect and Install Docker
SSH into your instance:
```bash
ssh -i "your-key.pem" ubuntu@<YOUR_EC2_PUBLIC_IP>
```

Install Docker and Docker Compose plugin:
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker ubuntu
```
Log out and reconnect (`exit` and re-ssh) so permissions take effect.

#### Step 3: Clone Repository and Launch
```bash
git clone -b feat/Frontend-Configured https://github.com/ANUJ760/PhishTank.git
cd PhishTank

# Start all three services (Postgres, Backend, Frontend with Nginx reverse proxy)
docker compose -f docker-compose.prod.yml up -d --build
```

#### Step 4: Verify Deployment
- Open your browser and navigate to: `http://<YOUR_EC2_PUBLIC_IP>`
- The Frontend loads immediately, with API calls automatically routed through Nginx to the FastAPI backend!

---

### ☁️ Guide 2: AWS App Runner (Backend) + S3 & CloudFront (Frontend)

#### Part A: Deploy Backend on AWS App Runner

1. **Create an Amazon ECR (Elastic Container Registry) Repository**:
   ```bash
   aws ecr create-repository --repository-name gecompose-backend --region us-east-1
   ```
2. **Build and push the Backend Docker image**:
   ```bash
   # Log in to ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

   # Build and tag
   docker build -t gecompose-backend -f Dockerfile .
   docker tag gecompose-backend:latest <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/gecompose-backend:latest

   # Push
   docker push <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/gecompose-backend:latest
   ```
3. **Create the App Runner Service**:
   - Go to **AWS App Runner** in the AWS Console → **Create Service**.
   - Source: **Container registry** → **Amazon ECR**.
   - Select `gecompose-backend:latest`.
   - Port: `8000`.
   - Environment variables:
     - `POSTGRES_HOST`: `<YOUR_RDS_HOST_OR_DB_ENDPOINT>`
     - `POSTGRES_DB`: `gecompose`
     - `POSTGRES_USER`: `gecompose`
     - `POSTGRES_PASSWORD`: `<YOUR_PASSWORD>`
   - Click **Create & Deploy**.
   - App Runner provides a live HTTPS URL (e.g., `https://xyz.us-east-1.awsapprunner.com`).

---

#### Part B: Deploy Frontend on Amazon S3 + CloudFront

1. **Build the production bundle**:
   ```bash
   cd frontend
   # Set your App Runner backend URL
   export VITE_API_URL="https://xyz.us-east-1.awsapprunner.com"
   npm run build
   ```
   This generates the optimized static files in `frontend/dist/`.

2. **Upload to an Amazon S3 Bucket**:
   ```bash
   # Create bucket
   aws s3 mb s3://gecompose-frontend-app --region us-east-1

   # Enable static website hosting
   aws s3 website s3://gecompose-frontend-app --index-document index.html --error-document index.html

   # Sync built files
   aws s3 sync dist/ s3://gecompose-frontend-app --delete
   ```

3. **Distribute globally with CloudFront**:
   - Go to **CloudFront** → **Create Distribution**.
   - **Origin domain**: Select your S3 bucket.
   - **Viewer protocol policy**: Redirect HTTP to HTTPS.
   - **Default root object**: `index.html`.
   - **Custom error response**:
     - HTTP error code: `403` and `404`
     - Response page path: `/index.html`
     - HTTP Response code: `200`
     *(This enables React Router client-side navigation without page refresh errors!)*

---

### ⚡ Option C: AWS Amplify (Easiest Managed Frontend)

If you prefer connecting your GitHub repository directly for zero-maintenance CI/CD:
1. Open **AWS Amplify Hosting**.
2. Click **Host web app** → Select **GitHub**.
3. Select repo `PhishTank` and branch `feat/Frontend-Configured`.
4. App directory: `frontend`.
5. Build settings:
   ```yaml
   frontend:
     phases:
       preBuild:
         commands:
           - npm ci
       build:
         commands:
           - npm run build
     artifacts:
       baseDirectory: dist
       files:
         - '**/*'
     cache:
       paths:
         - node_modules/**/*
   ```
6. Add environment variable: `VITE_API_URL` pointing to your Backend URL.
7. Click **Save and Deploy**. Every `git push` will now automatically build and deploy!

---

## 🛠️ Summary of Created Files

| File | Purpose |
|---|---|
| [`Dockerfile`](file:///d:/PhishTank/Dockerfile) | Production Python 3.11 container for the FastAPI/Uvicorn backend. |
| [`frontend/Dockerfile`](file:///d:/PhishTank/frontend/Dockerfile) | Multi-stage Dockerfile: builds Vite React app and serves via Alpine Nginx. |
| [`frontend/nginx.conf`](file:///d:/PhishTank/frontend/nginx.conf) | Nginx reverse proxy configuration routing `/api/` to backend and handling SPA fallback. |
| [`docker-compose.prod.yml`](file:///d:/PhishTank/docker-compose.prod.yml) | Orchestrates Postgres, Backend, and Frontend containers on an isolated bridge network. |
| [`frontend/src/vite-env.d.ts`](file:///d:/PhishTank/frontend/src/vite-env.d.ts) | TypeScript definitions for Vite client environment variables (`VITE_API_URL`). |
