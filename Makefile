run:
	python3 manage.py runserver
clean:
	python3 manage.py clearsession
collect:
	cd frontend && pnpm run build
	cp -f frontend/dist/assets/index.js website/static/assets/index.js
	cp -f frontend/dist/assets/index.css website/static/assets/index.css
	echo 'yes' | python3 manage.py collectstatic
makemigrations:
	python3 manage.py makemigrations
migrate:
	python3 manage.py migrate
shell:
	python3 manage.py shell
