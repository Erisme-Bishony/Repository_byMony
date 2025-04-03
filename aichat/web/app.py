from flask import Flask, request, render_template
import asyncio
from core.ai_chat import process_input

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
@app.route("/feedback", methods=["POST"])
async def index():
    if request.method == "POST":
        if "question" in request.form:
            user_input = request.form["question"]
            feedback = request.form.get("feedback", None)
            result = await process_input(user_input, feedback)
            return render_template(
                "index.html",
                question=user_input,
                result=result["result"].replace("\n", "<br>"),
                discussion_log="".join(result["discussion_log"]).replace("\n", "<br>")
            )
        elif "rating" in request.form:
            rating = request.form["rating"]
            feedback = f"用户评分: {rating}/5"
            return render_template(
                "index.html",
                feedback_message=f"感谢你的反馈！评分: {rating}/5"
            )
    return render_template("index.html")

if __name__ == "__main__":
    asyncio.run(app.run(debug=True, host="0.0.0.0", port=5000))