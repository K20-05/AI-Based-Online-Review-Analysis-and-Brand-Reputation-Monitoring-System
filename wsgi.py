from backend.app import app, start_background_services

start_background_services(debug_enabled=False)

application = app
