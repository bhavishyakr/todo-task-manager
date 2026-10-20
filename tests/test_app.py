import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_module


class TaskFlowTests(unittest.TestCase):
    def setUp(self):
        self.fd, self.path = tempfile.mkstemp(suffix=".db")
        app_module.app.config.update(DATABASE=self.path, TESTING=True)
        with app_module.app.app_context():
            app_module.init_db()
        self.client = app_module.app.test_client()

    def tearDown(self):
        os.close(self.fd)
        os.remove(self.path)

    def register(self, email="a@b.com"):
        return self.client.post("/api/register", json={"name": "Asha", "email": email, "password": "secret1"})

    def test_auth_flow(self):
        self.assertEqual(self.register().status_code, 201)
        self.assertEqual(self.register().status_code, 409)
        self.client.post("/api/logout")
        self.assertEqual(self.client.get("/api/tasks").status_code, 401)
        bad = self.client.post("/api/login", json={"email": "a@b.com", "password": "nope"})
        self.assertEqual(bad.status_code, 401)
        ok = self.client.post("/api/login", json={"email": "a@b.com", "password": "secret1"})
        self.assertEqual(ok.status_code, 200)

    def test_task_crud(self):
        self.register()
        r = self.client.post("/api/tasks", json={"title": "Write report", "priority": "high", "due_date": "2020-01-01"})
        self.assertEqual(r.status_code, 201)
        task = r.get_json()
        self.assertTrue(task["overdue"])
        tid = task["id"]

        self.assertEqual(self.client.post("/api/tasks", json={"title": " "}).status_code, 400)

        r = self.client.put(f"/api/tasks/{tid}", json={"title": "Write final report"})
        self.assertEqual(r.get_json()["title"], "Write final report")

        r = self.client.patch(f"/api/tasks/{tid}/toggle")
        self.assertTrue(r.get_json()["completed"])
        self.assertEqual(self.client.get("/api/stats").get_json()["percent"], 100)

        self.assertEqual(len(self.client.get("/api/tasks?status=active").get_json()), 0)
        self.assertEqual(self.client.delete("/api/tasks/completed").get_json()["deleted"], 1)
        self.assertEqual(self.client.delete(f"/api/tasks/{tid}").status_code, 404)

    def test_users_cannot_touch_each_others_tasks(self):
        self.register("one@x.com")
        tid = self.client.post("/api/tasks", json={"title": "Private"}).get_json()["id"]
        self.client.post("/api/logout")
        self.register("two@x.com")
        self.assertEqual(self.client.delete(f"/api/tasks/{tid}").status_code, 404)
        self.assertEqual(self.client.get("/api/tasks").get_json(), [])

    def test_search_and_filter(self):
        self.register()
        self.client.post("/api/tasks", json={"title": "Buy milk", "category": "Home", "priority": "low"})
        self.client.post("/api/tasks", json={"title": "Finish Java lab", "category": "College", "priority": "high"})
        self.assertEqual(len(self.client.get("/api/tasks?search=java").get_json()), 1)
        self.assertEqual(len(self.client.get("/api/tasks?category=Home").get_json()), 1)
        self.assertEqual(self.client.get("/api/tasks?priority=high").get_json()[0]["title"], "Finish Java lab")


if __name__ == "__main__":
    unittest.main()
