from flask import Flask, render_template, request
import subprocess

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    output = ""
    if request.method == "POST":
        try:
            result = subprocess.run(
                ["python3", "main.py"],  # Adjust filename
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout
        except subprocess.CalledProcessError as e:
            output = f"Error running script:\n{e.stderr}"
    return render_template("index.html", output=output)

if __name__ == "__main__":
    app.run(debug=True)
