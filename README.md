# 📡 S3 to RDS Data Ingestion Pipeline

This project implements a fully automated, event-driven ETL pipeline that ingests CSV data files from Amazon S3 and writes them into an Amazon RDS PostgreSQL database. The solution leverages AWS Lambda, Python, and the Serverless Framework for scalable and maintainable infrastructure management.

---

## 🎯 Objective

- Automatically trigger a Lambda function on new file uploads to a specific S3 bucket.
- Download, parse, and validate CSV files.
- Insert or upsert data into an RDS PostgreSQL table.
- Log events and errors via CloudWatch.
- Manage infrastructure using the Serverless Framework.

---

## ✅ Features & Acceptance Criteria

- ✅ **Trigger:** Lambda is invoked upon new uploads to an S3 bucket/prefix.
- ✅ **ETL Logic:**
  - Downloads file using `boto3`
  - Parses and validates CSV content
  - Connects to PostgreSQL with `psycopg2`
  - Inserts or upserts rows using transactions
- ✅ **Error Handling:**
  - Handles schema mismatches and DB failures gracefully
  - Logs all events and errors to CloudWatch
- ✅ **Deployment:**
  - Fully deployed and configured using the Serverless Framework
- ✅ **Code Quality:**
  - Modular, clean, and documented