import eventlet
eventlet.monkey_patch()

from app import app, socketio
import os

if __name__ == '__main__':
    # Configurações de produção
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print("=" * 50)
    print("FLASK-QUIZ - MODO PRODUÇÃO")
    print("=" * 50)
    print(f"Host: {host}")
    print(f"Porta: {port}")
    print(f"Debug: {app.debug}")
    print("Usando eventlet para async")
    print("=" * 50)
    
    socketio.run(
        app,
        host=host,
        port=port,
        debug=False,
        log_output=True,
        allow_unsafe_werkzeug=True
    )