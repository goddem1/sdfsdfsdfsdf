from flask_cors import CORS
from flask import Flask, request, jsonify, send_file

import calculation_engine


app = Flask(__name__)
CORS(app)
engine = calculation_engine.CalculationEngine()

WEBAPP_FILE = "webapp_index.html"


@app.route("/")
def index():
    # Подаём HTML мини‑аппа, который вызывает /api/calculate
    return send_file(WEBAPP_FILE)


@app.route("/api/calculate", methods=["POST", "OPTIONS"])
def api_calculate():
    if request.method == "OPTIONS":
        return "", 200

    try:
        if request.is_json:
            data = request.json
        else:
            data = request.form.to_dict()

        # Маппинг полей из UI в ожидаемые движком ключи
        field_mapping = {
            "utilizationCoefficient": "beta",
            "climateCoeffTO": "K_to",
            "climateCoeffRepair": "K_kr",
            "climateCoeffSpareParts": "K_zch",
        }

        mapped_data = {}
        for key, value in data.items():
            if key in ["routeNumber", "routeName", "model"]:
                continue
            mapped_data[field_mapping.get(key, key)] = value

        # Добавляем климатические коэффициенты, если их нет в входных данных
        if "climateZone" in mapped_data:
            climate_zone = mapped_data["climateZone"]
            climate_coeffs = engine.coefficients["climate"].get(climate_zone, {})
            if "K_to" not in mapped_data and "K_to" in climate_coeffs:
                mapped_data["K_to"] = climate_coeffs["K_to"]
            if "K_kr" not in mapped_data and "K_kr" in climate_coeffs:
                mapped_data["K_kr"] = climate_coeffs["K_kr"]
            if "K_zch" not in mapped_data and "K_zch" in climate_coeffs:
                mapped_data["K_zch"] = climate_coeffs["K_zch"]

        # Добавляем beta из routeType, если не пришло
        if "beta" not in mapped_data and "routeType" in mapped_data:
            route_type = mapped_data["routeType"]
            mapped_data["beta"] = engine.coefficients["beta"].get(route_type, 0.91)

        results = engine.calculate(mapped_data)
        if results.get("success"):
            return jsonify(results)

        return jsonify({"success": False, "error": results.get("error", "Неизвестная ошибка")}), 400

    except KeyError as e:
        return jsonify({"success": False, "error": f"Отсутствует обязательное поле ввода: {e}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Ошибка сервера: {str(e)}"}), 500


@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS":
        return "", 200

    try:
        if request.is_json:
            data = request.json
        else:
            data = request.form.to_dict()

        user_message = data.get("message", "")
        session_context = data.get("context")

        if not user_message:
            return jsonify({"response": "Пожалуйста, введите сообщение."}), 400

        ai_response = "Я вас понял. "
        if "k_pr" in user_message.lower() or "коэфф" in user_message.lower():
            if session_context and isinstance(session_context, dict):
                ai_response += (
                    f"Коэффициент K_пр был рассчитан на основе общего годового пробега и составляет "
                    f"{session_context.get('K_pr_used', 'неизвестно')}."
                )
            else:
                ai_response += (
                    "Коэффициент K_пр зависит от общего годового пробега и определяется по таблице в Приказе 402."
                )
        elif "nmck" in user_message.lower() or "цена" in user_message.lower():
            if session_context and isinstance(session_context, dict):
                ai_response += (
                    f"Начальная максимальная цена контракта (НМЦК) составляет "
                    f"{session_context.get('nmck_total', 'неизвестно')} рублей."
                )
            else:
                ai_response += "НМЦК рассчитывается по формуле: C × R × L_ijt × M_Sijt − P_t − C_суб."
        else:
            ai_response += "Задайте вопрос о расчете, и я постараюсь помочь."

        return jsonify({"response": ai_response})
    except Exception as e:
        return jsonify({"response": f"Ошибка при обработке запроса: {str(e)}"}), 500


@app.route("/api/download-excel", methods=["POST", "OPTIONS"])
def download_excel():
    from datetime import datetime
    import tempfile
    import os

    if request.method == "OPTIONS":
        return "", 200

    try:
        data = request.get_json(silent=True) or {}
        if "calculation_results" not in data:
            return jsonify({"error": "Нет данных для сохранения"}), 400

        results = data["calculation_results"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            temp_filename = tmp.name

        saved_file = engine.save_results_to_excel(results, temp_filename)
        if saved_file and os.path.exists(saved_file):
            return send_file(
                saved_file,
                as_attachment=True,
                download_name=f"nmck_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        return jsonify({"error": "Не удалось создать Excel файл"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Для разработки. В продакшене поднимайте через systemd/gunicorn.
    import os

    port = int(os.environ.get("PORT", "5050"))
    app.run(debug=True, host="0.0.0.0", port=port)

