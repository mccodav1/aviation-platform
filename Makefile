migrate:
	uv run manage.py migrate

migrations:
	uv run manage.py makemigrations

runserver:
	uv run manage.py runserver

reset: migrations migrate runserver
