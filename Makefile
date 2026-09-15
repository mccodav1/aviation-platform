migrate:
	uv run manage.py migrate

migrations:
	uv run manage.py makemigrations

runserver:
	uv run manage.py check_links
	uv run manage.py runserver

seed-media:
	uv run manage.py seed_media

load-demo:
	uv run manage.py loaddata core/fixtures/spa_demo.json meetings/fixtures/spa_demo.json

bootstrap: migrate seed-media load-demo

reset: migrations migrate runserver
