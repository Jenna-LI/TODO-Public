from flask import Flask
from flask_cors import CORS
import json
import functions
from flask import request

app = Flask(__name__)
CORS(app)



@app.route("/", methods= ['POST'])
def getTodoList():
    sentences = request.data.decode('utf-8')
    print('sentence:', sentences)
    result = functions.parse_todo_list(sentences)
    result = json.dumps(result)
    print(result)
    return result

app.run(host = '0.0.0.0')