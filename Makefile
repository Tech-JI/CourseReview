run: format
	python3 manage.py runserver
clean:
	python3 manage.py clearsession
collect:
	echo 'yes' | python3 manage.py collectstatic
format:
	isort .
	black .
makemigrations:
	python3 manage.py makemigrations
migrate:
	python3 manage.py migrate
shell:
	python3 manage.py shell
