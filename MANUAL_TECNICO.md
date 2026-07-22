# Manual Técnico

## Arquitectura
Navegador → FastAPI → SQLModel → SQLite/PostgreSQL

## Entidades
- User
- Transaction
- Budget
- SavingsGoal
- RecurringExpense

## Seguridad
- Contraseñas protegidas con bcrypt.
- Cookie HTTP-only para la interfaz.
- JWT Bearer para la API.
- Consultas filtradas por `user_id`.

## PostgreSQL
SQLite se utiliza por defecto. Para PostgreSQL, configura `DATABASE_URL`.
