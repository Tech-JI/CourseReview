from apps.spider.models import CrawledData

# from apps.spider.tasks import crawl_medians, crawl_orc, crawl_timetable
from apps.spider.tasks import crawl_orc
from website.celery import app


def crawl_and_import_data():
    old_task_always_eager = app.conf.task_always_eager
    app.conf.task_always_eager = True

    # ORC crawling takes a long time, especially when run synchronously.
    # If the ORC is not crawled, the course selection will only be limited,
    # but this should not interfere with development
    print("Crawling ORC. This will take a while.")
    crawl_orc()

    # print("Crawling timetable")
    # crawl_timetable()

    # print("Crawling medians")
    # crawl_medians()

    print("Importing ORC")
    _import_crawled_datas(CrawledData.ORC_DEPARTMENT_COURSES)

    # print("Importing timetable")
    # _import_crawled_datas(CrawledData.COURSE_TIMETABLE)

    # print("Importing medians")
    # _import_crawled_datas(CrawledData.MEDIANS)

    app.conf.task_always_eager = old_task_always_eager


def _import_crawled_datas(data_type):
    for crawled_data in CrawledData.objects.filter(data_type=data_type):
        if crawled_data.has_change():
            crawled_data.approve_change()
