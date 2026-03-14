from app_main import app
from routes.whisper.shibie import shibie
# from server_upload import server_files_cache  # 已改为系统定时任务，不再在 Flask 中启动
import threading
from stslib import tool
import os

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Thread(target=tool.checkupdate, daemon=True).start()
        threading.Thread(target=shibie, daemon=True).start()

    app.run(
        host="0.0.0.0",
        port=5026,
        debug=True
    )
