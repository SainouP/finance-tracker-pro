# Finance Tracker Pro V5

Aplicación web de finanzas personales desarrollada con FastAPI, SQLModel,
Chart.js, JWT y una interfaz responsive.

## Funcionalidades

- Registro e inicio de sesión.
- Información financiera privada por usuario.
- Ingresos, gastos, categorías y métodos de pago.
- Balance general y resumen mensual.
- Comparación de ingresos, gastos y ahorro contra el mes anterior.
- Puntaje de salud financiera de 0 a 100.
- Presupuestos mensuales con progreso.
- Metas de ahorro descontadas del saldo.
- Bloqueo visual de metas completadas.
- Gastos recurrentes pagables una sola vez por mes.
- Estado de pagos: pendiente, próximo, vencido o pagado.
- Historial de pagos recurrentes.
- Financial Insights persistentes.
- Historial de insights con filtros y estado revisado.
- Gráficos por categoría, día, mes y año.
- Búsqueda y ordenamiento de movimientos.
- Exportación CSV.
- Tema claro y oscuro.
- API REST con Swagger.
- Docker, pruebas y GitHub Actions.
- SQLite local y PostgreSQL mediante `DATABASE_URL`.

## Instalación local

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Aplicación:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

Usuario demo:

```text
demo@finance.com
Demo123
```

## Pruebas

```powershell
python -m pytest -q
```

## Publicar en GitHub

```powershell
git init
git add .
git commit -m "feat: release Finance Tracker Pro V5"
git branch -M main
git remote add origin URL_DE_TU_REPOSITORIO
git push -u origin main
```

## Despliegue en Render

### Build command

```text
pip install -r requirements.txt
```

### Start command

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Variables de entorno

```text
SECRET_KEY=<cadena larga y segura>
DATABASE_URL=<URL de PostgreSQL>
PYTHON_VERSION=3.12.8
```

No uses SQLite para producción si necesitas conservar los datos después de cada
nuevo despliegue. Utiliza una base PostgreSQL persistente.

## Licencia

MIT.
