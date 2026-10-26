# Setup: Claude → GitHub → Instagram + YouTube

```
 Claude Code (this folder)            GitHub (PeaceCrack/thestoiccommunicator, public)
 ─────────────────────────            ───────────────────────────────────────────────
 /stoic-communicator-post             stores posts/ and out/<slug>/ (JPEGs, MP4s)
 writes + renders a post        ──►   Action "Publish post" runs publish.py with your secrets
 you say "push" in the chat                │                    │
                                           ▼                    ▼
                                    Instagram Reel       YouTube Short
```

Allow about an hour, once. Parts 1-5 are one-time. After that, each post is just
`/stoic-communicator-post` → review → "push".

Meta and Google rename menus from time to time. If a button below has a slightly different
name, pick the closest match.

**Golden rule for every key and token below:** never paste it into the chat, a file in this
folder, or a commit. Each one goes straight into a GitHub secret with `gh secret set`, which
reads it with hidden input.

---

## Part 1. Tools on this Mac (5 min)

```bash
brew install gh
```

```bash
gh auth login
```

Pick **GitHub.com → HTTPS → Login with a web browser**, and sign in as **PeaceCrack**.

---

## Part 2. Instagram: make the account professional (2 min)

In the Instagram app, logged in as **@thestoiccommunicator**:

1. Profile → ☰ → **Settings and activity** → **Account type and tools**.
2. **Switch to professional account** → **Creator** (or Business) → category e.g. *Education* or *Author*.

No Facebook Page is needed.

---

## Part 3. Instagram: create a new Meta app and a token (15 min)

### 3.1 Developer account
Go to **https://developers.facebook.com** → **Get Started**, log in with Facebook, and verify
email/phone if asked.

### 3.2 Create the app
1. **My Apps** → **Create App**.
2. App name `Stoic Publisher`, your contact email.
3. Use case: **Manage messaging & content on Instagram**.
4. Business portfolio: **I don't want to connect a business portfolio yet**.
5. **Create app**, re-enter your Facebook password.

### 3.3 Permissions
Left menu → **Use cases** → **Customize** (Instagram) → **API setup with Instagram login** →
under **Permissions** make sure both are added:
- `instagram_business_basic`
- `instagram_business_content_publish`

### 3.4 Make @thestoiccommunicator a tester
The app stays in **Development mode**, which is fine: it only needs to post to accounts with a
role on it.

1. **App roles** → **Roles** → **Add People** → **Instagram Tester** → `thestoiccommunicator`.
2. Accept: on instagram.com logged in as @thestoiccommunicator → **Settings** → **Website
   permissions** → **Apps and websites** → **Tester invites** → **Accept**.

### 3.5 Generate the token and find the account ID
1. Back in **API setup with Instagram login** → **Generate access tokens** → **Add account** →
   log in as **@thestoiccommunicator** → approve.
2. Click **Generate token**. This is a long-lived token, valid **60 days** (Part 7 refreshes it).
   Copy it into your password manager, nowhere else.
3. The number shown next to the account is the **IG user ID** (`IG_USER_ID`). Note that
   `thestoiccommunicator` is the username; the ID is a long number like `17841400000000000`.

Check both from a terminal. The first line asks for the token with hidden input:

```bash
read -s IG_ACCESS_TOKEN && export IG_ACCESS_TOKEN
```

```bash
curl -s -G https://graph.instagram.com/v23.0/me --data-urlencode "fields=user_id,username" --data-urlencode "access_token=$IG_ACCESS_TOKEN"
```

It should print `"username": "thestoiccommunicator"` and the `user_id`.

---

## Part 4. YouTube: Google Cloud project and sign-in (20 min)

Use the Google account that owns (or manages) the channel
**https://www.youtube.com/channel/UCMN3YKY4HjY4H8enFRvvshg**.

### 4.1 Create the project
1. Open **https://console.cloud.google.com** and sign in.
2. Top bar → project picker → **New project** → name `stoic-publisher` → **Create**.
3. Make sure the picker now shows `stoic-publisher`.

### 4.2 Turn on the YouTube API
1. ☰ → **APIs & Services** → **Library**.
2. Search **YouTube Data API v3** → open it → **Enable**.

### 4.3 Consent screen (Google Auth Platform)
1. ☰ → **APIs & Services** → **OAuth consent screen** (it opens **Google Auth Platform**) →
   **Get started**.
2. App name `Stoic Publisher`, support email = your email → **Next**.
3. Audience: **External** → **Next**. Contact email → **Next**. Agree → **Create**.
4. **Data access** → **Add or remove scopes** → filter and tick:
   - `.../auth/youtube.upload`
   - `.../auth/youtube.readonly`
   → **Update** → **Save**.
5. **Audience** → **Publish app** → **Confirm**, so the status says **In production**.
   *Why:* in "Testing" status Google expires refresh tokens after 7 days and uploads would stop
   every week. You do **not** need Google's verification for this: you are the only user. You'll
   just see a "Google hasn't verified this app" warning once when you sign in.

### 4.4 Create the OAuth client
1. **Clients** → **Create client** → Application type **Desktop app** → name `stoic-desktop` →
   **Create**.
2. **Download JSON**. It saves `client_secret_XXXX.json` in Downloads. Keep it out of this
   folder (`.gitignore` blocks it anyway).

### 4.5 Sign in once and store the YouTube secrets
From this folder:

```bash
cd "/Users/madhur/Downloads/Madhur Personal/Stoic_communicator"
```

```bash
python3 youtube_auth.py ~/Downloads/client_secret_XXXX.json
```

A browser opens:
1. Pick your Google account, then the **The Stoic Communicator** channel if it asks.
2. "Google hasn't verified this app" → **Advanced** → **Go to Stoic Publisher (unsafe)**.
   It's your own app, so this is expected.
3. Tick both permissions → **Continue**.

The script checks you picked channel `UCMN3YKY4HjY4H8enFRvvshg`, then saves `YT_CLIENT_ID`,
`YT_CLIENT_SECRET` and `YT_REFRESH_TOKEN` as GitHub secrets without printing them. (Run Part 5.1
first if the repo has no commits yet; `gh secret set` needs the repo to exist, which it does.)

### 4.6 Important: the YouTube audit (uploads start out private)
Google locks every video uploaded through an **unverified API project** as **private**. The
Shorts upload automatically, but nobody can see them until the project passes Google's free
compliance audit. To lift the lock:

1. Fill in the **YouTube API Services – Audit and Quota Extension Form**:
   https://support.google.com/youtube/contact/yt_api_form
2. Describe it truthfully: "Uploads my own original Shorts to my own channel
   (UCMN3YKY4HjY4H8enFRvvshg) from a GitHub Action. Single user. No other users' data."
   Link the public repo as the implementation.
3. Approval usually takes days to a few weeks. Until then, either leave the Shorts private, or
   upload `out/<slug>/reel.mp4` in the YouTube app by hand. The Action records the video ID either way.

To upload as unlisted or private on purpose, set a repo **variable** (not a secret):
**Settings → Secrets and variables → Actions → Variables → New** `YT_PRIVACY` = `private`.

The default quota (10,000 units a day) covers about 6 uploads a day.

---

## Part 5. GitHub repo and Instagram secrets (10 min)

### 5.1 First push of the pipeline
Claude makes the first commit and push when you ask. It contains no posts, so nothing gets published.
The repo must stay **public**, because Instagram downloads the media from it.

### 5.2 Instagram secrets
Each command asks for the value with hidden input:

```bash
gh secret set IG_USER_ID
```

```bash
gh secret set IG_ACCESS_TOKEN
```

### 5.3 Let the workflow record what it posted
github.com/PeaceCrack/thestoiccommunicator → **Settings** → **Actions** → **General** →
**Workflow permissions** → **Read and write permissions** → **Save**.

Check all five secrets are there:

```bash
gh secret list
```

You should see `IG_USER_ID`, `IG_ACCESS_TOKEN`, `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

---

## Part 6. Every post

In Claude Code, in this folder: `/stoic-communicator-post`.

1. Claude rolls a random creative brief and suggests 4 topics. Pick one (or type your own).
2. A background agent researches the story, quotes and facts, writes the post, then renders
   the reel. It **does not push**.
3. Claude shows you a frame sheet and sends you `out/<slug>/reel.mp4` to watch.
4. Say **push**. Claude commits, pushes and watches the GitHub run, then reports the
   Reel and Short IDs.

To retry only one platform: Actions → **Publish post** → **Run workflow** → post file, `only` =
`youtube` or `ig_reel`, untick dry run.

---

## Part 7. Refresh the Instagram token (every ~50 days)

```bash
read -s IG_ACCESS_TOKEN && export IG_ACCESS_TOKEN
```

```bash
curl -s -G https://graph.instagram.com/refresh_access_token --data-urlencode "grant_type=ig_refresh_token" --data-urlencode "access_token=$IG_ACCESS_TOKEN" | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'], end='')" | gh secret set IG_ACCESS_TOKEN
```

If it already expired, generate a new one (3.5). The YouTube refresh token doesn't expire
unless you revoke it, change your Google password, or leave it unused for 6 months.

---

## Troubleshooting

| Error in the Action log | Fix |
|---|---|
| `Missing environment variables: IG_...` | An Instagram secret is missing or misspelled (5.2). |
| `Missing environment variables: YT_...` | Run `youtube_auth.py` again (4.5). |
| `HTTP 400 ... Invalid OAuth access token` / code 190 | Instagram token expired. Refresh it (Part 7). |
| `HTTP 403` / code 10 or 200 | `instagram_business_content_publish` missing (3.3), or token is for another account. |
| `Container ... failed with status ERROR` | Instagram couldn't fetch or read a file. Open the URLs from a dry run in a private window. |
| `invalid_grant` from oauth2.googleapis.com | YouTube refresh token revoked or expired (app left in Testing?). Check 4.3 step 5, rerun 4.5. |
| `HTTP 403 ... quotaExceeded` | More than ~6 uploads today. Wait until midnight Pacific time. |
| `HTTP 401 ... youtubeSignupRequired` | You signed in with an account without that channel. Rerun 4.5 and pick the channel. |
| Short is private | Expected until the audit passes (4.6). |
| `git push` fails in "Record what was posted" | Workflow permissions aren't read and write (5.3). |
