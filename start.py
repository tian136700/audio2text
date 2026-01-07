from app_main import app

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5023,
        debug=True,
        use_reloader=True
    )
