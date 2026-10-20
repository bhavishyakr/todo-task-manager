const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");
const errBox = document.getElementById("auth-error");

function showTab(which) {
  const isLogin = which === "login";
  loginForm.hidden = !isLogin;
  registerForm.hidden = isLogin;
  tabLogin.classList.toggle("active", isLogin);
  tabRegister.classList.toggle("active", !isLogin);
  tabLogin.setAttribute("aria-selected", isLogin);
  tabRegister.setAttribute("aria-selected", !isLogin);
  errBox.hidden = true;
}
tabLogin.onclick = () => showTab("login");
tabRegister.onclick = () => showTab("register");

async function submit(form, url) {
  errBox.hidden = true;
  const body = Object.fromEntries(new FormData(form));
  const btn = form.querySelector("button[type=submit]");
  btn.disabled = true;
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Something went wrong.");
    window.location.href = "/";
  } catch (e) {
    errBox.textContent = e.message;
    errBox.hidden = false;
  } finally {
    btn.disabled = false;
  }
}

loginForm.addEventListener("submit", (e) => { e.preventDefault(); submit(loginForm, "/api/login"); });
registerForm.addEventListener("submit", (e) => { e.preventDefault(); submit(registerForm, "/api/register"); });
