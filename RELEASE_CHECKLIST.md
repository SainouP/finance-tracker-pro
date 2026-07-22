# Release Checklist

## Antes de subir a GitHub

- [ ] Ejecutar `python -m pytest -q`.
- [ ] Revisar que `.env` y la base local no estén versionadas.
- [ ] Cambiar `SECRET_KEY` en producción.
- [ ] Revisar capturas del README.
- [ ] Confirmar que el repositorio sea público.
- [ ] Añadir descripción y temas al repositorio.

## Antes de desplegar

- [ ] Crear PostgreSQL.
- [ ] Configurar `DATABASE_URL`.
- [ ] Configurar `SECRET_KEY`.
- [ ] Configurar `PYTHON_VERSION=3.12.8`.
- [ ] Verificar `/health`.
- [ ] Verificar registro e inicio de sesión.
- [ ] Verificar creación de movimientos.
- [ ] Verificar pagos recurrentes.
- [ ] Verificar metas e insights.
- [ ] Verificar modo oscuro y vista móvil.
