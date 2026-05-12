import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv('TODOIST_API_TOKEN')
API_URL = 'https://api.todoist.com/api/v1'
REST_API_URL = 'https://api.todoist.com/rest/v2'

headers = {'Authorization': f'Bearer {API_TOKEN}'}

# test getting tasks
res = requests.get(f"{API_URL}/projects", headers=headers)
if res.status_code == 200:
    projects = res.json()
    if projects:
        p_id = projects[0]['id']
        print(f"Project ID: {p_id}")
        # get tasks
        res2 = requests.get(f"{API_URL}/tasks", headers=headers, params={'project_id': p_id})
        tasks = res2.json()
        print(f"Tasks: {len(tasks)}")
        if tasks:
            t_id = tasks[0]['id']
            print(f"Task ID: {t_id}")
            # get comments
            res3 = requests.get(f"{API_URL}/comments", headers=headers, params={'task_id': t_id})
            print(f"Comments /api/v1/comments: {res3.status_code} - {res3.text[:100]}")
            
            res4 = requests.get(f"{REST_API_URL}/comments", headers=headers, params={'task_id': t_id})
            print(f"Comments /rest/v2/comments: {res4.status_code} - {res4.text[:100]}")
else:
    print(res.status_code, res.text)
