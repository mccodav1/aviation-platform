# Deploying

The deployed stack is four compose services, built from this repo's
source on the server (no image registry):

```
browser -> nginx (:80/:443) -> web (gunicorn + Django) -> db (Postgres)
              |                   |
         media volume (ro)   media + private_media volumes
```

- **nginx** serves `/media/` straight off the media volume and proxies
  everything else to gunicorn. It never mounts `private_media`. It also
  rate-limits logins and the public Join/Contact forms per IP (see
  "Rate limits" below), and terminates HTTPS once it's turned on.
- **web** runs `migrate` and `ensure_superuser` on every start, then gunicorn. Static files are
  collected into the image at build time and served by WhiteNoise.
- **db** is Postgres 17; its data lives in the `pgdata` volume.
- **certbot** renews the HTTPS certificate when it's close to expiring.
  It does nothing until `make cert` has fetched one.

All configuration lives in `.env`. See `.env.example` for every setting,
split into MANDATORY and OPTIONAL.

## First deploy (e.g. a fresh Lightsail instance)

Install Docker Engine + the compose plugin, then:

```
git clone git@github.com:mccodav1/aviation-platform.git
cd aviation-platform
cp .env.example .env
# Fill in the MANDATORY section: secret key, the server's public IP in
# DJANGO_ALLOWED_HOSTS, the admin email/password, and a Postgres
# password.

make up                  # docker compose up -d --build (creates the admin account)
make compose-seed        # optional: load the current site content
```

The site comes up empty but working after `make up`. `make compose-seed`
(`bootstrap_site`) is the separate, one-time step that copies the
tracked seed images/documents into the volumes and loads the fixtures,
so the site looks the way it does in development. It refuses to run once
content exists, because re-loading fixtures would overwrite officers'
edits.

In the Lightsail firewall (networking tab), open only ports 22 (SSH),
80 and 443. Postgres and gunicorn are never published, so nothing else
needs to be reachable.

Make `DJANGO_SUPERUSER_PASSWORD` long and random. `/admin` is the first
thing bots try, and this password skips the usual strength checks. It's
only used to create the account the first time; after that, change it in
`/admin`.

Before giving anyone an account, turn on HTTPS (below). Over plain HTTP,
every password typed on the site crosses the network readable.

## Updating

```
git pull
make up
```

This rebuilds the `web` image and restarts it. Migrations run
automatically on start. Expect a few seconds of downtime.

To roll back, check out the previous commit or tag and `make up` again.
A migration that already ran is not undone by this. Reverse it with
`docker compose exec web python manage.py migrate <app> <previous>` first.

## Adding a domain name

1. Point the domain's DNS at the instance's static IP.
2. Add it to `DJANGO_ALLOWED_HOSTS` in `.env` (comma-separated, keep the IP
   if it should still work).
3. `docker compose up -d` to restart with the new value.

nginx's server blocks are catch-alls, so they need no change for this.
Once HTTPS is on, the domain also has to be on the certificate: add it
to `CERT_DOMAINS` and run `make cert` again.

## Enabling HTTPS

Free certificates from Let's Encrypt, fetched once by `make cert` and
renewed automatically by the certbot service. Needs a domain name - a
bare IP can't get one.

1. Point the domain (and `www.`, if wanted) at the server, and add both
   to `DJANGO_ALLOWED_HOSTS` (see above). Check that
   `http://yourdomain/` loads.
2. In `.env`, set the certificate's domains and an email to register the
   Let's Encrypt account with:

   ```
   CERT_DOMAINS=salinaspilots.org,www.salinaspilots.org
   CERT_EMAIL=you@example.com
   ```

3. `make cert`. Let's Encrypt checks the domain over port 80, so the
   stack has to be up and port 80 open. It ends with "Successfully
   received certificate".
4. Switch nginx and Django over, in `.env`:

   ```
   NGINX_SITE=https
   DJANGO_HTTPS=true
   ```

5. `make up`. `http://` now redirects to `https://`, and Django turns on
   secure-only cookies and HSTS.

Do step 4 only after step 3 succeeds: nginx won't start on `https`
without the certificate, and Django with `DJANGO_HTTPS=true` but no
HTTPS makes logging in impossible. To back out, set both back
(`NGINX_SITE=http`, `DJANGO_HTTPS=false`) and `make up`. Browsers that
already visited over HTTPS keep insisting on it for up to 30 days
(HSTS), so back out only to fix HTTPS, not to stay on HTTP.

Renewal needs no attention: certbot checks twice a day and renews within
30 days of expiry, and nginx reloads every 6 hours to pick it up.

Nothing warns you if renewal stops working - Let's Encrypt stopped
sending expiry emails in 2025. To check it now and then:

```
docker compose run --rm --entrypoint certbot certbot certificates           # expiry date
docker compose run --rm --entrypoint certbot certbot renew --dry-run        # practice renewal
```

A free uptime monitor that watches certificate expiry (e.g. UptimeRobot)
can warn you automatically.

## Rate limits

nginx limits how often one IP address can submit (POST) these forms. Loading
pages is never limited.

| Form                          | Limit                                  |
|-------------------------------|----------------------------------------|
| `/login/`, `/admin/login/`    | a burst of 10, then one every 6 seconds |
| `/join`, `/contact`           | a burst of 5, then one every 20 seconds |

Past that, nginx shows a short "Too many tries - wait a minute" page
(status 429). The numbers are in `docker/nginx/00-rate-limits.conf`.
This sits on top of Django's own login lockout (5 wrong passwords for one
email from one IP locks that pair out for 15 minutes; officers can clear
it with Unlock on the Users page).

The Join and Contact forms also have a hidden honeypot field that only
bots fill in. Those submissions are dropped without being saved, behind
the usual thank-you page (see `HoneypotMixin` in `core/forms.py`).

If the site ever sits behind a load balancer or CDN (Lightsail's
included), nginx sees that service's address instead of the visitor's,
so every visitor would share one limit. The rate limits would need
nginx's `real_ip` settings first.

## Day-to-day

```
make logs                                    # nginx + gunicorn + Postgres logs
docker compose exec web python manage.py ... # any management command
docker compose exec db psql -U aviation      # database shell
```

## What's state and what isn't

Back up these three volumes. Everything else is rebuilt from the repo.

| Volume          | Holds                                                      |
|-----------------|------------------------------------------------------------|
| `pgdata`        | The Postgres database                                      |
| `media`         | Public uploads: logo, hero/card/about images               |
| `private_media` | Gated uploads: meeting agendas/minutes and every Resource file |

The `letsencrypt` volume holds the HTTPS certificate. It's worth keeping,
but not critical: if it's lost, `make cert` gets a new one.

`staticfiles/` is a build artifact (regenerated by `collectstatic` in
every image build) and deliberately not a volume.

### Backups

```
make backup                                     # -> backups/<date_time>/
make restore BACKUP=backups/2026-10-15_030000   # asks before replacing anything
```

`make backup` saves the database (`db.sql.gz`) and both upload volumes
(`files.tgz`) while the site keeps running. `make restore` stops the site,
replaces the database and uploads with that backup, and starts it again.
`backups/` is git- and docker-ignored.

A backup on the server's own disk won't survive losing the server - copy
`backups/` somewhere else (your computer, cloud storage). To back up
nightly, add a cron job on the server (`crontab -e`), e.g. 3am:

```
0 3 * * * cd /path/to/aviation-platform && mkdir -p backups && make backup >> backups/cron.log 2>&1
```

Old backups aren't deleted automatically; prune them now and then.

## Upgrading Postgres

**Minor versions** (17.1 -> 17.2) need nothing special: they arrive with
the next `make up`.

**Major versions** (17 -> 18) are a migration, not a one-line change.
Postgres can't read an older major version's data files, so bumping only
the `image:` tag leaves the database refusing to start. Postgres 18's
image also expects its volume mounted at `/var/lib/postgresql` rather
than `/var/lib/postgresql/data` - with the old mount it stops with
`Error: in 18+, these Docker images are configured to store database
data in a format which is compatible with "pg_ctlcluster"...`.

The move is backup -> empty database on the new version -> restore.
Using a *new* volume keeps the old one untouched as a fallback:

1. `make backup` - note the folder it prints.
2. `make down`
3. In `compose.yaml`, under `db:`
   - change the image tag, e.g. `postgres:18-alpine`;
   - change the volume line to a new volume name and, for 18+, the new
     mount path: `- pgdata18:/var/lib/postgresql`;
   - add `pgdata18:` to the `volumes:` list at the bottom.
4. `make up` - starts on the new version with an empty database (`web`
   creates the tables and the `.env` admin account on start).
5. `make restore BACKUP=backups/<the folder from step 1>`
6. Check the site. To roll back instead, put the old image tag and
   volume line back and `make up`.
7. Once you're happy, delete the old volume:
   `docker volume rm aviation-platform_pgdata`, and remove `pgdata:` from
   the `volumes:` list.

(Rehearsed 17 -> 18 on 2026-10-15: data, accounts and uploads all came
through.) Read the release notes for the new major version first, and
check the image's page on Docker Hub for any further changes.

## Email: not set up yet

The site has no outgoing mail configured (no `EMAIL_*` settings). Things
waiting on it:

- **Password reset is turned off.** The routes are left out of
  `config/urls.py`, with instructions there for turning them back on.
  Until then, reset a forgotten password in `/admin` -> Users.
- **Contact-message notifications** are attempted (to the
  organization's email) but fail quietly; officers read messages on
  `/messages` instead.
- **Welcome packets** - approving an application only activates the
  account for now (see `JoinRequest.decide` in `core/models.py`).

## Invariants to preserve

- **`private_media` is never publicly served.** Its files are reachable
  only through Django's gated views (`resource_download`, the meeting
  agenda/minutes views). A Resource marked "public" means *no login
  required*, not *raw public URL*. Never mount `private_media` into
  nginx or add a URL route for it. `PrivateFileSystemStorage.url()`
  raises on purpose.
- **Times are stored in UTC and shown in the visitor's browser
  timezone.** `static/js/timezone.js` sets a `tz` cookie that
  `core/middleware/timezone.py` activates per request.
  `DJANGO_TIME_ZONE` is only the fallback for a visitor whose zone isn't
  known yet. Display times through timezone-aware paths (`|date`,
  `timezone.localtime()`), never raw formatting of the stored value.
- **One deployment per organization.** The `Organization` table is a
  single-row site configuration, not multi-tenancy.
- **Accounts log in by email, not a username.** The user model is
  `core.User` (`AUTH_USER_MODEL`). Applying on the Join page creates an
  inactive account with the applicant's chosen password; approving the
  application on `/applications` activates it.
- **Roles are a ladder of groups:** Member (no group) < Site admin
  ("Site Admins") < Officer ("Club Officers") < Superadmin (superuser).
  Each can do everything the one below can. Site admins get
  meetings/events, resources, site content, and account support
  (unlocking accounts, resetting passwords, creating accounts); officers
  add membership applications, contact messages, and changing someone's
  role; superusers can do everything, and are the only ones who can
  delete users. An account holds one role.
  Each group's permissions are listed in `core/permissions.py` and synced
  after every `migrate` (so on container start too) - add new ones there,
  not in a data migration. Give an account a role with the Role picker on
  the Users page, which also sets `is_staff` to match.
- **Officers and Site Admins can't escalate.** The admin hides superuser
  status and individual permissions from non-superusers, limits the
  groups they can assign to the two role groups, and won't let them edit
  a superuser's account (see `UserAdmin` in `core/admin.py`). Keep that
  if the user admin changes.
