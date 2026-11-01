from rest_framework.pagination import PageNumberPagination


class CoursePaginator(PageNumberPagination):
    page_size = 10  # элементов на странице по умолчанию
    page_size_query_param = "page_size"  # ?page_size=5
    max_page_size = 50  # верхняя граница


class LessonPaginator(PageNumberPagination):
    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 20
