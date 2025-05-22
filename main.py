import scratchattach as sa,os,requests,urllib.parse,uuid,threading,urllib.parse,json,time,base64,warnings;warnings.filterwarnings('ignore', category=sa.LoginDataWarning)

import conversion

session = sa.login("username", "password")
cloud = session.connect_cloud("1166477703")
client = cloud.requests(no_packet_loss=True, respond_order="finish")

TOGETHER = "together.ai API KEY"

generations = {}

SAVE_DIR = "saves"
os.makedirs(SAVE_DIR, exist_ok=True)
SAVE_LOG = os.path.join(SAVE_DIR, "_logs.json")

log_lock = threading.Lock()

@client.event
def on_ready():
    print("Request handler is running")

@client.request
def ping():
    print(f"Ping request received")
    return "pong"

def detect_nsfw(res):
    input_str = res.text
    n = len(input_str)
    for i in range(n):
        if input_str[i] == '{':
            balance = 1
            in_string = False
            escape = False
            start = i
            for j in range(i + 1, n):
                char = input_str[j]
                if in_string:
                    if escape:
                        escape = False
                    else:
                        if char == '\\':
                            escape = True
                        elif char == '"':
                            in_string = False
                else:
                    if char == '{':
                        balance += 1
                    elif char == '}':
                        balance -= 1
                    elif char == '"':
                        in_string = True
                if balance == 0:
                    json_str = input_str[start:j+1]
                    try:
                        data = json.loads(json_str)
                        return data.get("has_nsfw_concept", False) or data.get("isMature", False)
                    except json.JSONDecodeError:
                        break  # Invalid JSON, try next possible start
    return None  # Or raise an exception if JSON is expected


def run_generation(prompt, id):
    try:
            res = requests.get(
                f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1024&height=1024&nologo=True&private=True&safe=True",
            )
            if res.status_code == 200:
                if detect_nsfw(res):
                    generations[id]["status"] = "nfe"
                    generations[id]["result"] = "NFE Content detected"
                else:
                    generations[id]["status"] = "done"
                    generations[id]["result"] = base64.b64encode(res.content)
            else:
                raise Exception(res.text)
                generations[id]["status"] = "error"
                generations[id]["result"] = res.text
    except Exception as e:
        #generations[id]["status"] = "error"
        #generations[id]["result"] = str(e)
        try:
            res = requests.post(
                "https://api.together.xyz/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {TOGETHER}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "black-forest-labs/FLUX.1-schnell-Free",
                    "prompt": prompt,
                    "steps": 4,
                    "n": 1,
                    "height": 1024,
                    "width": 1024,
                    "response_format": "base64"
                }
            )
            if res.status_code == 200:
                data = res.json()["data"][0]["b64_json"]
                generations[id]["status"] = "done"
                generations[id]["result"] = data
            else:
                generations[id]["status"] = "error"
                generations[id]["result"] = res.text
        except Exception as e2:
            generations[id]["status"] = "error"
            generations[id]["result"] = str(e2) + "\n\n" + str(e)
    finally:
        if generations[id]["status"] == "done":
            with open(os.path.join(SAVE_DIR, id + ".jpeg"), 'wb') as f:
                f.write(base64.b64decode(generations[id]["result"]))

        with log_lock:
            with open(SAVE_LOG, 'r') as f2:
                current_logs = json.load(f2)

			# if status not done: include the full generations[id] (including the error "result"). else: include all the keys except the "result" key. this is because the result would already have been written to the jpeg.
            current_logs[id] = generations[id] if not generations[id]["status"] == "done" else {key: value for key, value in generations[id].items() if not key == "result"}

            with open(SAVE_LOG, 'w') as f2:
                json.dump(current_logs, f2, indent=2)
            

@client.request
def gen_image(prompt):
    print(f"Queuing generation for {prompt}")
    id = str(uuid.uuid4())
    generations[id] = {"prompt": prompt, "status": "running", "result": None, "username": str(client.get_requester())}
    threading.Thread(target=run_generation, args=(prompt, id)).start()
    return id

@client.request
def generation_status(id):
    print(f"Retrieving generation status for generation {id}")
    if generations.get(id):
        print(generations[id]["status"])
        return generations[id]["status"]
    else:
        return "NOT FOUND"
    
@client.request
def generation_response(id, size):
    if not size:
        return "a"
    print(f"Retrieving generation response for generation {id} | {size}")
    if generations.get(id):
        if not generations[id]["status"] == "done":
            generations[id]["result"] or "NOT COMPLETE"
        else:
            raw_img = base64.b64decode(generations[id]["result"])
            return conversion.convert_img(raw_img, int(size))
        
    else:
        return "NOT FOUND"
    
client.start()
