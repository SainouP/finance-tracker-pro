from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
import calendar, csv, io
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from .database import create_db_and_tables, engine, get_session
from .models import *
from .security import authenticate, create_token, current_api_user, current_web_user, hash_password

BASE_DIR = Path(__file__).resolve().parent
MONTHS_ES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

def add_insight(session, user_id, insight_type, title, message, event_key):
    exists = session.exec(select(FinancialInsight).where(
        FinancialInsight.user_id == user_id,
        FinancialInsight.event_key == event_key
    )).first()
    if not exists:
        session.add(FinancialInsight(
            user_id=user_id, insight_type=insight_type, title=title,
            message=message, event_key=event_key
        ))

def seed_demo(session: Session):
    if session.exec(select(User)).first():
        return
    user = User(full_name="Usuario Demo", email="demo@finance.com",
                password_hash=hash_password("Demo123"), monthly_income_target=3000,
                financial_goal="Construir un fondo de emergencia")
    session.add(user); session.commit(); session.refresh(user)
    today = date.today()
    session.add_all([
        Transaction(user_id=user.id, transaction_type=TransactionType.INCOME, category=Category.SALARY,
                    amount=3000, description="Sueldo mensual", payment_method=PaymentMethod.TRANSFER,
                    transaction_date=today.replace(day=1)),
        Transaction(user_id=user.id, transaction_type=TransactionType.EXPENSE, category=Category.FOOD,
                    amount=420, description="Alimentación del mes", payment_method=PaymentMethod.CARD,
                    transaction_date=today.replace(day=min(5, today.day))),
        Transaction(user_id=user.id, transaction_type=TransactionType.EXPENSE, category=Category.TRANSPORT,
                    amount=180, description="Transporte", payment_method=PaymentMethod.YAPE,
                    transaction_date=today.replace(day=min(10, today.day))),
        Transaction(user_id=user.id, transaction_type=TransactionType.EXPENSE, category=Category.ENTERTAINMENT,
                    amount=120, description="Streaming y ocio", payment_method=PaymentMethod.CARD,
                    transaction_date=today.replace(day=min(15, today.day))),
    ])
    session.add(Budget(user_id=user.id, category=Category.FOOD, monthly_limit=700,
                       month=today.month, year=today.year))
    session.add(SavingsGoal(user_id=user.id, name="Laptop nueva", target_amount=5000, current_amount=1850))
    session.add(RecurringExpense(user_id=user.id, name="Internet", category=Category.SERVICES,
                                 amount=100, due_day=15))
    session.commit()

@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        seed_demo(session)
    yield

app = FastAPI(title="Finance Tracker Pro", version="5.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

def web_user(request, session):
    user = current_web_user(request, session)
    return user or RedirectResponse("/login", status_code=303)

def owned(model, item_id, user_id, session):
    item = session.get(model, item_id)
    if not item or item.user_id != user_id:
        raise HTTPException(404, "Registro no encontrado")
    return item

def build_dashboard(user_id, session):
    today = date.today()
    txs = session.exec(select(Transaction).where(Transaction.user_id == user_id)
                       .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())).all()
    income = sum(t.amount for t in txs if t.transaction_type == TransactionType.INCOME)
    expenses = sum(t.amount for t in txs if t.transaction_type == TransactionType.EXPENSE)
    current = [t for t in txs if t.transaction_date.month == today.month and t.transaction_date.year == today.year]
    month_income = sum(t.amount for t in current if t.transaction_type == TransactionType.INCOME)
    month_expenses = sum(t.amount for t in current if t.transaction_type == TransactionType.EXPENSE)

    expense_categories = [c for c in Category if c not in {Category.SALARY, Category.FREELANCE}]
    category_values = {c.value: sum(t.amount for t in current if
        t.transaction_type == TransactionType.EXPENSE and t.category == c) for c in expense_categories}

    budgets = session.exec(select(Budget).where(
        Budget.user_id == user_id, Budget.month == today.month, Budget.year == today.year)).all()
    budget_rows = []
    for b in budgets:
        spent = category_values.get(b.category.value, 0)
        budget_rows.append({"budget": b, "spent": spent,
                            "percent": round(spent / b.monthly_limit * 100, 1) if b.monthly_limit else 0})

    goals = session.exec(select(SavingsGoal).where(SavingsGoal.user_id == user_id)).all()
    recurring = session.exec(select(RecurringExpense).where(
        RecurringExpense.user_id == user_id, RecurringExpense.is_active == True)).all()
    payments = session.exec(select(RecurringPayment).where(
        RecurringPayment.user_id == user_id,
        RecurringPayment.month == today.month,
        RecurringPayment.year == today.year)).all()
    paid_ids = {p.recurring_id for p in payments}
    recurring_rows = []
    for r in recurring:
        due = date(today.year, today.month, min(r.due_day, calendar.monthrange(today.year, today.month)[1]))
        paid = r.id in paid_ids
        days = (due - today).days
        status = "Pagado" if paid else ("Vencido" if days < 0 else ("Vence hoy" if days == 0 else f"Vence en {days} días"))
        recurring_rows.append({"item": r, "paid": paid, "due_date": due, "status": status, "days": days})
    recurring_rows.sort(key=lambda row: (row["paid"], row["due_date"]))

    period = f"{today.year}-{today.month:02d}"
    if month_income:
        rate = (month_income-month_expenses)/month_income*100
        add_insight(session, user_id, InsightType.SAVINGS, "Tasa de ahorro",
                    f"Tu tasa de ahorro de {MONTHS_ES[today.month-1]} es {rate:.0f}%.",
                    f"savings-rate-{period}-{round(rate)}")
    if category_values and max(category_values.values(), default=0) > 0:
        top_name, top_value = max(category_values.items(), key=lambda x:x[1])
        add_insight(session, user_id, InsightType.TREND, "Mayor categoría de gasto",
                    f"{top_name} lidera tus gastos del mes con S/ {top_value:.2f}.",
                    f"top-category-{period}-{top_name}-{round(top_value,2)}")
    for row in budget_rows:
        if row["percent"] >= 100:
            add_insight(session, user_id, InsightType.ALERT, "Presupuesto excedido",
                        f"Superaste el presupuesto de {row['budget'].category.value}.",
                        f"budget-exceeded-{period}-{row['budget'].category.value}")
        elif row["percent"] >= 80:
            add_insight(session, user_id, InsightType.BUDGET, "Presupuesto cerca del límite",
                        f"Ya utilizaste {row['percent']:.0f}% del presupuesto de {row['budget'].category.value}.",
                        f"budget-warning-{period}-{row['budget'].category.value}-{int(row['percent']//5)*5}")
    for g in goals:
        progress = min(g.current_amount/g.target_amount*100, 100)
        if progress >= 100:
            add_insight(session, user_id, InsightType.GOAL, "Meta completada",
                        f"Completaste la meta “{g.name}”.", f"goal-complete-{g.id}")
    for row in recurring_rows:
        if not row["paid"] and row["days"] <= 3:
            add_insight(session, user_id, InsightType.PAYMENT, "Pago próximo",
                        f"{row['item'].name}: {row['status'].lower()}.",
                        f"payment-due-{period}-{row['item'].id}-{row['status']}")
    session.commit()

    insights = session.exec(select(FinancialInsight).where(
        FinancialInsight.user_id == user_id).order_by(FinancialInsight.created_at.desc())).all()
    chart_rows = [{"date":t.transaction_date.isoformat(),"category":t.category.value,"amount":t.amount}
                  for t in txs if t.transaction_type == TransactionType.EXPENSE]
    years = sorted({t.transaction_date.year for t in txs} | {today.year}, reverse=True)
    if today.month == 1:
        previous_month, previous_year = 12, today.year - 1
    else:
        previous_month, previous_year = today.month - 1, today.year

    previous = [
        t for t in txs
        if t.transaction_date.month == previous_month
        and t.transaction_date.year == previous_year
    ]
    previous_income = sum(
        t.amount for t in previous if t.transaction_type == TransactionType.INCOME
    )
    previous_expenses = sum(
        t.amount for t in previous if t.transaction_type == TransactionType.EXPENSE
    )
    previous_savings = previous_income - previous_expenses
    current_savings = month_income - month_expenses

    def variation(current_value, previous_value):
        if previous_value == 0:
            return None if current_value == 0 else 100.0
        return round((current_value - previous_value) / abs(previous_value) * 100, 1)

    income_variation = variation(month_income, previous_income)
    expense_variation = variation(month_expenses, previous_expenses)
    savings_variation = variation(current_savings, previous_savings)

    savings_rate = (
        ((month_income - month_expenses) / month_income) * 100
        if month_income > 0 else 0
    )
    budget_control = (
        sum(1 for row in budget_rows if row["percent"] <= 100) / len(budget_rows) * 100
        if budget_rows else 70
    )
    paid_control = (
        sum(1 for row in recurring_rows if row["paid"]) / len(recurring_rows) * 100
        if recurring_rows else 70
    )
    positive_balance = 100 if income - expenses >= 0 else 0
    health_score = round(max(0, min(
        100,
        savings_rate * 1.8 + budget_control * 0.25 + paid_control * 0.2 + positive_balance * 0.25
    )))
    if health_score >= 80:
        health_label = "Excelente"
    elif health_score >= 60:
        health_label = "Buena"
    elif health_score >= 40:
        health_label = "En desarrollo"
    else:
        health_label = "Necesita atención"

    top_category = None
    if category_values and max(category_values.values(), default=0) > 0:
        top_category = max(category_values.items(), key=lambda item: item[1])

    closest_goal = None
    incomplete_goals = [g for g in goals if g.current_amount < g.target_amount]
    if incomplete_goals:
        closest = max(incomplete_goals, key=lambda g: g.current_amount / g.target_amount)
        closest_goal = {
            "name": closest.name,
            "percent": round(closest.current_amount / closest.target_amount * 100, 1),
        }

    payment_history = session.exec(
        select(RecurringPayment)
        .where(RecurringPayment.user_id == user_id)
        .order_by(RecurringPayment.paid_at.desc())
    ).all()
    recurring_by_id = {r.id: r for r in recurring}
    payment_history_rows = []
    for payment in payment_history:
        recurring_item = recurring_by_id.get(payment.recurring_id)
        transaction = session.get(Transaction, payment.transaction_id)
        if recurring_item and transaction:
            payment_history_rows.append({
                "name": recurring_item.name,
                "amount": transaction.amount,
                "month_name": MONTHS_ES[payment.month - 1],
                "year": payment.year,
                "paid_at": payment.paid_at,
            })

    return dict(
        transactions=txs,
        income=income,
        expenses=expenses,
        balance=income-expenses,
        month_income=month_income,
        month_expenses=month_expenses,
        current_savings=current_savings,
        income_variation=income_variation,
        expense_variation=expense_variation,
        savings_variation=savings_variation,
        previous_month_name=MONTHS_ES[previous_month - 1],
        category_values=category_values,
        budgets=budget_rows,
        goals=goals,
        recurring=recurring_rows,
        payment_history=payment_history_rows,
        insights=insights[:4],
        insight_history=insights,
        chart_rows=chart_rows,
        years=years,
        health_score=health_score,
        health_label=health_label,
        top_category=top_category,
        closest_goal=closest_goal,
    )

@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})

@app.post("/login", response_class=HTMLResponse, include_in_schema=False)
def login_web(request: Request, email: str = Form(...), password: str = Form(...), session: Session = Depends(get_session)):
    user = authenticate(email, password, session)
    if not user:
        return templates.TemplateResponse(request=request, name="login.html", context={"error":"Correo o contraseña incorrectos"}, status_code=401)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("session_token", create_token(user), httponly=True, samesite="lax", max_age=14400)
    return response

@app.get("/register", response_class=HTMLResponse, include_in_schema=False)
def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={"error":None})

@app.post("/register", include_in_schema=False)
def register_web(full_name: str=Form(...), email: str=Form(...), password: str=Form(...), session: Session=Depends(get_session)):
    email=email.lower().strip()
    if session.exec(select(User).where(User.email==email)).first():
        raise HTTPException(409,"El correo ya existe")
    session.add(User(full_name=full_name.strip(),email=email,password_hash=hash_password(password))); session.commit()
    return RedirectResponse("/login",303)

@app.get("/logout", include_in_schema=False)
def logout():
    response=RedirectResponse("/login",303); response.delete_cookie("session_token"); return response

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard(request: Request, session: Session=Depends(get_session)):
    user=web_user(request,session)
    if isinstance(user,RedirectResponse): return user
    return templates.TemplateResponse(request=request,name="dashboard.html",context={
        "user":user, **build_dashboard(user.id,session), "categories":list(Category),
        "expense_categories":[c for c in Category if c not in {Category.SALARY,Category.FREELANCE}],
        "transaction_types":list(TransactionType),"payment_methods":list(PaymentMethod),
        "insight_types":list(InsightType),"months":list(enumerate(MONTHS_ES,1)),
        "current_month":date.today().month,"current_year":date.today().year,"today":date.today().isoformat()
    })

@app.post("/web/transactions", include_in_schema=False)
def transaction_web(request:Request,transaction_type:TransactionType=Form(...),category:Category=Form(...),
 amount:float=Form(...),description:str=Form(...),payment_method:PaymentMethod=Form(...),
 transaction_date:str=Form(...),session:Session=Depends(get_session)):
    user=web_user(request,session)
    if isinstance(user,RedirectResponse): return user
    session.add(Transaction(user_id=user.id,transaction_type=transaction_type,category=category,amount=amount,
                description=description.strip(),payment_method=payment_method,transaction_date=date.fromisoformat(transaction_date)))
    session.commit(); return RedirectResponse("/",303)

@app.post("/web/transactions/{item_id}/delete", include_in_schema=False)
def transaction_delete(item_id:int,request:Request,session:Session=Depends(get_session)):
    user=web_user(request,session)
    if isinstance(user,RedirectResponse): return user
    item=owned(Transaction,item_id,user.id,session); session.delete(item); session.commit(); return RedirectResponse("/",303)

@app.post("/web/budgets", include_in_schema=False)
def budget_web(request:Request,category:Category=Form(...),monthly_limit:float=Form(...),
 month:int=Form(...),year:int=Form(...),session:Session=Depends(get_session)):
    user=web_user(request,session)
    if isinstance(user,RedirectResponse): return user
    existing=session.exec(select(Budget).where(Budget.user_id==user.id,Budget.category==category,
        Budget.month==month,Budget.year==year)).first()
    if existing: existing.monthly_limit=monthly_limit; session.add(existing)
    else: session.add(Budget(user_id=user.id,category=category,monthly_limit=monthly_limit,month=month,year=year))
    session.commit(); return RedirectResponse("/",303)

@app.post("/web/goals", include_in_schema=False)
def goal_web(request:Request,name:str=Form(...),target_amount:float=Form(...),current_amount:float=Form(0),
 target_date:str=Form(""),session:Session=Depends(get_session)):
    user=web_user(request,session)
    if isinstance(user,RedirectResponse): return user
    session.add(SavingsGoal(user_id=user.id,name=name.strip(),target_amount=target_amount,current_amount=current_amount,
                target_date=date.fromisoformat(target_date) if target_date else None))
    session.commit(); return RedirectResponse("/",303)

@app.post("/web/goals/{goal_id}/contribute", include_in_schema=False)
def goal_contribute(goal_id:int,request:Request,amount:float=Form(...),
 payment_method:PaymentMethod=Form(PaymentMethod.TRANSFER),session:Session=Depends(get_session)):
    user=web_user(request,session)
    if isinstance(user,RedirectResponse): return user
    goal=owned(SavingsGoal,goal_id,user.id,session)
    remaining=max(goal.target_amount-goal.current_amount,0); contribution=min(amount,remaining)
    balance=build_dashboard(user.id,session)["balance"]
    if contribution<=0:return RedirectResponse("/?notice=goal-complete",303)
    if contribution>balance:return RedirectResponse("/?notice=insufficient-balance",303)
    goal.current_amount+=contribution; session.add(goal)
    session.add(Transaction(user_id=user.id,transaction_type=TransactionType.EXPENSE,category=Category.SAVINGS,
                amount=contribution,description=f"Aporte a meta: {goal.name}",payment_method=payment_method))
    if goal.current_amount>=goal.target_amount:
        add_insight(session,user.id,InsightType.GOAL,"Meta completada",f"Completaste la meta “{goal.name}”.",f"goal-complete-{goal.id}")
    session.commit(); return RedirectResponse("/?notice=goal-contribution",303)

@app.post("/web/recurring", include_in_schema=False)
def recurring_web(request:Request,name:str=Form(...),category:Category=Form(...),amount:float=Form(...),
 due_day:int=Form(...),session:Session=Depends(get_session)):
    user=web_user(request,session)
    if isinstance(user,RedirectResponse): return user
    duplicate=session.exec(select(RecurringExpense).where(RecurringExpense.user_id==user.id,
        RecurringExpense.name==name.strip(),RecurringExpense.is_active==True)).first()
    if duplicate:return RedirectResponse("/?notice=duplicate-recurring",303)
    session.add(RecurringExpense(user_id=user.id,name=name.strip(),category=category,amount=amount,due_day=due_day))
    session.commit(); return RedirectResponse("/",303)

@app.post("/web/recurring/{recurring_id}/pay", include_in_schema=False)
def recurring_pay(recurring_id:int,request:Request,payment_method:PaymentMethod=Form(PaymentMethod.TRANSFER),
 session:Session=Depends(get_session)):
    user=web_user(request,session)
    if isinstance(user,RedirectResponse): return user
    item=owned(RecurringExpense,recurring_id,user.id,session); today=date.today()
    already=session.exec(select(RecurringPayment).where(RecurringPayment.user_id==user.id,
        RecurringPayment.recurring_id==item.id,RecurringPayment.month==today.month,
        RecurringPayment.year==today.year)).first()
    if already:return RedirectResponse("/?notice=already-paid",303)
    if item.amount>build_dashboard(user.id,session)["balance"]:return RedirectResponse("/?notice=insufficient-balance",303)
    tx=Transaction(user_id=user.id,transaction_type=TransactionType.EXPENSE,category=item.category,
        amount=item.amount,description=f"Pago recurrente: {item.name}",payment_method=payment_method)
    session.add(tx); session.commit(); session.refresh(tx)
    session.add(RecurringPayment(user_id=user.id,recurring_id=item.id,transaction_id=tx.id,
        month=today.month,year=today.year))
    add_insight(session,user.id,InsightType.PAYMENT,"Pago registrado",
        f"Pagaste {item.name} por S/ {item.amount:.2f}.",f"payment-paid-{today.year}-{today.month}-{item.id}")
    session.commit(); return RedirectResponse("/?notice=recurring-paid",303)

@app.post("/web/insights/{insight_id}/review", include_in_schema=False)
def review_insight(insight_id:int,request:Request,session:Session=Depends(get_session)):
    user=web_user(request,session)
    if isinstance(user,RedirectResponse): return user
    insight=owned(FinancialInsight,insight_id,user.id,session); insight.is_reviewed=True
    session.add(insight); session.commit(); return RedirectResponse("/#insight-history",303)

@app.post("/web/profile", include_in_schema=False)
def profile_web(request:Request,currency:str=Form(...),monthly_income_target:float=Form(0),
 financial_goal:str=Form(""),session:Session=Depends(get_session)):
    user=web_user(request,session)
    if isinstance(user,RedirectResponse): return user
    user.currency=currency.upper().strip(); user.monthly_income_target=monthly_income_target
    user.financial_goal=financial_goal.strip() or None; session.add(user); session.commit()
    return RedirectResponse("/?notice=profile-updated",303)

@app.get("/web/export/csv",include_in_schema=False)
def export_csv(request:Request,session:Session=Depends(get_session)):
    user=web_user(request,session)
    if isinstance(user,RedirectResponse): return user
    txs=session.exec(select(Transaction).where(Transaction.user_id==user.id).order_by(Transaction.transaction_date.desc())).all()
    output=io.StringIO(); writer=csv.writer(output); writer.writerow(["Fecha","Tipo","Categoría","Descripción","Método","Monto"])
    for t in txs:writer.writerow([t.transaction_date,t.transaction_type.value,t.category.value,t.description,t.payment_method.value,t.amount])
    return StreamingResponse(iter([output.getvalue()]),media_type="text/csv",
        headers={"Content-Disposition":"attachment; filename=movimientos_financieros.csv"})

@app.post("/api/auth/login",response_model=TokenResponse,tags=["Autenticación"])
def api_login(data:LoginRequest,session:Session=Depends(get_session)):
    user=authenticate(data.email,data.password,session)
    if not user:raise HTTPException(401,"Credenciales incorrectas")
    return TokenResponse(access_token=create_token(user),user_name=user.full_name)

@app.get("/api/summary",tags=["Dashboard"])
def api_summary(session:Session=Depends(get_session),user:User=Depends(current_api_user)):
    d=build_dashboard(user.id,session)
    return {k:d[k] for k in ("income","expenses","balance","month_income","month_expenses")}

@app.get("/api/transactions",tags=["Movimientos"])
def api_transactions(session:Session=Depends(get_session),user:User=Depends(current_api_user)):
    return session.exec(select(Transaction).where(Transaction.user_id==user.id)).all()

@app.post("/api/transactions",status_code=201,tags=["Movimientos"])
def api_transaction(data:TransactionCreate,session:Session=Depends(get_session),user:User=Depends(current_api_user)):
    item=Transaction(user_id=user.id,**data.model_dump());session.add(item);session.commit();session.refresh(item);return item

@app.post("/api/budgets",status_code=201,tags=["Presupuestos"])
def api_budget(data:BudgetCreate,session:Session=Depends(get_session),user:User=Depends(current_api_user)):
    item=Budget(user_id=user.id,**data.model_dump());session.add(item);session.commit();session.refresh(item);return item

@app.post("/api/goals",status_code=201,tags=["Metas"])
def api_goal(data:GoalCreate,session:Session=Depends(get_session),user:User=Depends(current_api_user)):
    item=SavingsGoal(user_id=user.id,**data.model_dump());session.add(item);session.commit();session.refresh(item);return item

@app.post("/api/goals/{goal_id}/contribute",tags=["Metas"])
def api_goal_contribute(goal_id:int,data:GoalContribution,session:Session=Depends(get_session),user:User=Depends(current_api_user)):
    goal=owned(SavingsGoal,goal_id,user.id,session);remaining=max(goal.target_amount-goal.current_amount,0)
    amount=min(data.amount,remaining)
    if amount<=0:raise HTTPException(400,"La meta ya está completa")
    if amount>build_dashboard(user.id,session)["balance"]:raise HTTPException(400,"Saldo insuficiente")
    goal.current_amount+=amount;session.add(goal)
    session.add(Transaction(user_id=user.id,transaction_type=TransactionType.EXPENSE,category=Category.SAVINGS,
        amount=amount,description=f"Aporte a meta: {goal.name}",payment_method=PaymentMethod.TRANSFER))
    session.commit();session.refresh(goal);return goal

@app.post("/api/recurring",status_code=201,tags=["Recurrentes"])
def api_recurring(data:RecurringCreate,session:Session=Depends(get_session),user:User=Depends(current_api_user)):
    item=RecurringExpense(user_id=user.id,**data.model_dump());session.add(item);session.commit();session.refresh(item);return item

@app.post("/api/recurring/{recurring_id}/pay",status_code=201,tags=["Recurrentes"])
def api_recurring_pay(recurring_id:int,session:Session=Depends(get_session),user:User=Depends(current_api_user)):
    item=owned(RecurringExpense,recurring_id,user.id,session);today=date.today()
    if session.exec(select(RecurringPayment).where(RecurringPayment.user_id==user.id,
        RecurringPayment.recurring_id==item.id,RecurringPayment.month==today.month,
        RecurringPayment.year==today.year)).first():raise HTTPException(409,"Este pago ya fue registrado este mes")
    tx=Transaction(user_id=user.id,transaction_type=TransactionType.EXPENSE,category=item.category,
        amount=item.amount,description=f"Pago recurrente: {item.name}",payment_method=PaymentMethod.TRANSFER)
    session.add(tx);session.commit();session.refresh(tx)
    session.add(RecurringPayment(user_id=user.id,recurring_id=item.id,transaction_id=tx.id,month=today.month,year=today.year))
    session.commit();return tx

@app.get("/health",tags=["Sistema"])
def health():return {"status":"ok","version":"5.0.0"}
