# Privacy Policy: Stoic Publisher

*Last updated: 20 October 2026*

Stoic Publisher is a private publishing tool run by the owner of **The Stoic Communicator**
(Instagram [@thestoiccommunicator](https://www.instagram.com/thestoiccommunicator/) and the YouTube
channel [UCMN3YKY4HjY4H8enFRvvshg](https://www.youtube.com/channel/UCMN3YKY4HjY4H8enFRvvshg)).
Its only job is to upload the owner's own original posts and videos to the owner's own accounts.
The source code is public in this repository.

## Who uses it

Only the account owner. It has no other users, no sign-up and no public interface.

## What data it accesses

- **YouTube** (Google OAuth scopes `youtube.upload` and `youtube.readonly`): it uploads videos to the
  owner's channel, and reads the channel's ID once to confirm it is the right channel.
- **Instagram** (`instagram_business_basic`, `instagram_business_content_publish`): it publishes
  posts and reels to the owner's account.

It does not read, collect or store anyone else's data, viewers' data, comments, messages or analytics.

## How credentials are stored

OAuth tokens are stored only as encrypted GitHub Actions secrets in this repository. They are never
written to files, logs or the code. Nothing is sold, shared or sent to any third party other than
Google/YouTube and Meta/Instagram themselves, and only to publish the owner's content.

## Google API Services

Stoic Publisher's use of information received from Google APIs follows the
[Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy),
including the Limited Use requirements. It also follows the
[YouTube API Services Terms of Service](https://developers.google.com/youtube/terms/api-services-terms-of-service),
and uploaded videos are subject to the [Google Privacy Policy](https://policies.google.com/privacy).

## Revoking access

The owner can revoke access at any time at https://myaccount.google.com/permissions (Google) and in
Instagram under Settings → Website permissions → Apps and websites.

## Contact

madhursharma24@gmail.com
