# Aviation Platform

Django site for the Salinas Pilots Association (SPA). Site content (hero
images, nav, cards, info panels) is data-driven through the Django admin
rather than hardcoded in templates, with the goal of eventually reusing this
codebase as a template for other flying clubs (each on its own deployment).

## Setup

```
uv sync
make bootstrap   # migrate + seed_media + loaddata (demo content/images)
make runserver
```

`db.sqlite3` and `media/` aren't committed — `make bootstrap` reconstructs
them from `base_images/` (tracked seed images) and the fixtures under
`core/fixtures/` and `meetings/fixtures/`.
