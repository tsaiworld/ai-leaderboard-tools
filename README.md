
# AI Tools Leaderboard – Brian Tsai (Portrait · One-Page · Auto-Refresh)

This is a **static website** you can publish **without Google Drive**. It renders a clean, portrait-style leaderboard and is ready to **print to 1 page**.  

## Publish in 3 minutes (GitHub Pages)
1. Create a GitHub repo (e.g., `ai-tools-leaderboard`).
2. Upload all files in this folder to the repo (keep the `.github/workflows` folder).
3. In GitHub: Settings → Pages → set **Source: GitHub Actions** (no branch selection needed).
4. Push; the included workflow will deploy automatically. You’ll get a public URL like:
   `https://<your-username>.github.io/ai-tools-leaderboard/`

## Daily Automatic Refresh (9:00 AM Central Time)
This repo includes a workflow that runs **daily at 14:00 UTC** (≈ 9:00 AM CT) to bump a timestamp and re-deploy, ensuring the page shows a fresh update time.

- Workflow file: `.github/workflows/daily-refresh.yml`
- You can change the schedule by editing the cron line.

## Update Content
- Edit **leaderboard.json** to change ranks, add tools, or modify notes.
- The site reads JSON at load, so no build step is required.
- For quick edits in GitHub, click the file, **Edit**, then **Commit**.

## Print to 1 Page
- Use your browser's **Print** dialog → Layout: **Portrait**; Scale: 90%–100% as needed.
- The CSS includes print tweaks to keep cells readable.

---

---

### 🔄 Re-publish Site
Need to rebuild or redeploy the leaderboard manually?  
Click below to trigger a fresh GitHub Pages deployment:

[![Re-publish Site](https://img.shields.io/badge/Re--publish%20Site-Trigger%20Deploy-blue?style=for-the-badge&logo=github)](../../actions/workflows/deploy.yml)

---
© 2025 Brian Tsai Consulting
