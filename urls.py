from django.urls import path
from . import views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('', views.expenses_index, name="expenses"),  # Updated to use expenses_index
    path('add-expense', views.add_expense, name="add-expenses"),
    path('edit-expense/<int:id>', views.edit_expense, name="expense-edit"),
    path('expense-delete/<int:id>', views.delete_expense, name="expense-delete"),
    path('search-expenses', csrf_exempt(views.search_expenses), name="search_expenses"),
    path('expense_category_summary', views.expense_category_summary, name="expense_category_summary"),
    path('stats', views.expenses_stats_view, name="stats"),
    path('export_CSV', views.export_CSV, name="export-CSV"),
    path('export_excel', views.export_excel, name="export-excel"),
    path('export-pdf', views.export_pdf, name="export-pdf")  

   
]

