from todoist_api_python.api import TodoistAPI

api = TodoistAPI("874b527c4061e519eb927828b5d76da2f67f521d")

task = api.get_task("6f3q9vhwwCW6v9xh")
print(f"Task: {task.content}")

comments_iter = api.get_comments(task_id=task.id)
for comments in comments_iter:
    for comment in comments:
        print(f"Comment: {comment.content}")