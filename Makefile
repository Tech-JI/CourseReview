run:
	python3 manage.py runserver
clean:
	python3 manage.py clearsession
collect:
	npm run build
	python3 manage.py collectstatic
migrate:
	python3 manage.py migrate
shell:
	python3 manage.py shell
