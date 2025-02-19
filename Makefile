run:
	python3 manage.py runserver
clean:
	python3 manage.py clearsession
collect:
	npm run build
	python3 manage.py collectstatic
makemigrations:
	python3 manage.py makemigrations
migrate:
	python3 manage.py migrate
shell:
	python3 manage.py shell
