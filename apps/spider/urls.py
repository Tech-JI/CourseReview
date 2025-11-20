from django.urls import re_path

from apps.spider import views as spider_views

urlpatterns = [
    re_path(r"^data/$", spider_views.crawled_data_list, name="crawled_datas"),
    re_path(
        r"^data/(?P<crawled_data_pk>[0-9]+)$",
        spider_views.crawled_data_detail,
        name="crawled_data",
    ),
]
