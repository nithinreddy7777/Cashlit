from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from .models import Category, Expense
from userpreferences.models import UserPreference
from userincome.models import Source, UserIncome
import json
import datetime
import csv
import xlwt

from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile
from django.db import models
from django.db.models import Sum


# === COMMON SEARCH ===
def search_expenses(request):
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText')
        expenses = Expense.objects.filter(owner=request.user)
        expenses = expenses.filter(
            amount__istartswith=search_str) | expenses.filter(
            date__istartswith=search_str) | expenses.filter(
            description__icontains=search_str) | expenses.filter(
            category__icontains=search_str)
        data = expenses.values()
        return JsonResponse(list(data), safe=False)

def search_income(request):
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText')
        income = UserIncome.objects.filter(owner=request.user)
        income = income.filter(
            amount__istartswith=search_str) | income.filter(
            date__istartswith=search_str) | income.filter(
            description__icontains=search_str) | income.filter(
            source__icontains=search_str)
        data = income.values()
        return JsonResponse(list(data), safe=False)

# === EXPENSES ===
@login_required(login_url='/authentication/login')
def expenses_index(request):
    categories = Category.objects.all()
    expenses = Expense.objects.filter(owner=request.user)
    paginator = Paginator(expenses, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    user_preference, _ = UserPreference.objects.get_or_create(user=request.user, defaults={'currency': 'INR'})
    currency = user_preference.currency

    context = {
        'expenses': expenses,
        'page_obj': page_obj,
        'currency': currency
    }
    return render(request, 'expenses/index.html', context)

@login_required(login_url='/authentication/login')
def add_expense(request):
    categories = Category.objects.all()
    context = {'categories': categories, 'values': request.POST}

    if request.method == 'GET':
        return render(request, 'expenses/add_expense.html', context)

    amount = request.POST.get('amount')
    description = request.POST.get('description')
    date = request.POST.get('expense_date')
    category = request.POST.get('category')

    if not amount or not description or not category or not date:
        messages.error(request, 'All fields are required')
        return render(request, 'expenses/add_expense.html', context)

    Expense.objects.create(owner=request.user, amount=amount, date=date, category=category, description=description)
    messages.success(request, 'Expense saved successfully')
    return redirect('expenses')

@login_required(login_url='/authentication/login')
def edit_expense(request, id):
    expense = Expense.objects.get(pk=id)
    categories = Category.objects.all()
    context = {'expense': expense, 'values': expense, 'categories': categories}

    if request.method == 'GET':
        return render(request, 'expenses/edit-expense.html', context)

    amount = request.POST.get('amount')
    description = request.POST.get('description')
    date = request.POST.get('expense_date')
    category = request.POST.get('category')

    if not amount or not description or not category or not date:
        messages.error(request, 'All fields are required')
        return render(request, 'expenses/edit-expense.html', context)

    expense.owner = request.user
    expense.amount = amount
    expense.date = date
    expense.category = category
    expense.description = description
    expense.save()

    messages.success(request, 'Expense updated successfully')
    return redirect('expenses')

@login_required(login_url='/authentication/login')
def delete_expense(request, id):
    expense = Expense.objects.get(pk=id)
    expense.delete()
    messages.success(request, 'Expense removed')
    return redirect('expenses')

@login_required(login_url='/authentication/login')
def expenses_stats_view(request):
    return render(request, 'expenses/stats.html')

@login_required(login_url='/authentication/login')
def expense_category_summary(request):
    today_date = datetime.date.today()
    six_months_ago = today_date - datetime.timedelta(days=30 * 6)
    expenses = Expense.objects.filter(owner=request.user, date__gte=six_months_ago, date__lte=today_date)
    finalrep = {}

    def get_category(expenses):
        return expenses.category

    category_list = list(set(map(get_category, expenses)))

    def get_expenses_category_amount(category):
        amount = 0
        filtered_by_category = expenses.filter(category=category)
        for item in filtered_by_category:
            amount += item.amount
        return amount

    for y in category_list:
        finalrep[y] = get_expenses_category_amount(y)

    return JsonResponse({'expense_category_data': finalrep}, safe=False)

# === EXPORT CSV ===
@login_required(login_url='/authentication/login')
def export_CSV(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename=Expenses_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv'

    writer = csv.writer(response)
    writer.writerow(['Amount', 'Description', 'Category', 'Date'])

    expenses = Expense.objects.filter(owner=request.user)
    for expense in expenses:
        writer.writerow([expense.amount, expense.description, expense.category, expense.date])

    return response

# === EXPORT EXCEL ===
@login_required(login_url='/authentication/login')
def export_excel(request):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename=Expenses_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xls'

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Expenses')

    row_num = 0
    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    columns = ['Amount', 'Description', 'Category', 'Date']
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)

    font_style = xlwt.XFStyle()

    rows = Expense.objects.filter(owner=request.user).values_list('amount', 'description', 'category', 'date')

    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            ws.write(row_num, col_num, str(row[col_num]), font_style)

    wb.save(response)
    return response

# === EXPORT PDF ===
@login_required(login_url='/authentication/login')
def export_pdf(request):
    expenses = Expense.objects.filter(owner=request.user)
    sum = expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    html_string = render_to_string('expenses/pdf-output.html', {
        'expenses': expenses,
        'total': sum
    })

    html = HTML(string=html_string)
    result = html.write_pdf()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline;attachment; filename=Expenses_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.pdf'
    response['Content-Transfer-Encoding'] = 'binary'

    with tempfile.NamedTemporaryFile(delete=True) as output:
        output.write(result)
        output.flush()
        output.seek(0)
        response.write(output.read())

    return response
