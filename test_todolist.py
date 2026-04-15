#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import init_db
from todolist import get_all_todos, add_todo, update_todo_completed, delete_todo

def test_todolist():
    print("初始化数据库...")
    init_db()
    
    print("添加测试任务...")
    todo1 = add_todo("测试任务1")
    todo2 = add_todo("测试任务2")
    print(f"添加了任务: {todo1.title}, {todo2.title}")
    
    print("获取所有任务...")
    todos = get_all_todos()
    for todo in todos:
        print(f"任务: {todo.title}, 完成: {todo.completed}")
    
    print("更新任务完成状态...")
    if todos:
        update_todo_completed(todos[0].id, True)
        print(f"更新任务 {todos[0].title} 为已完成")
    
    print("再次获取所有任务...")
    todos = get_all_todos()
    for todo in todos:
        print(f"任务: {todo.title}, 完成: {todo.completed}")
    
    print("删除任务...")
    if len(todos) > 1:
        delete_todo(todos[1].id)
        print(f"删除任务 {todos[1].title}")
    
    print("最终任务列表:")
    todos = get_all_todos()
    for todo in todos:
        print(f"任务: {todo.title}, 完成: {todo.completed}")
    
    print("测试完成!")

if __name__ == "__main__":
    test_todolist()