import streamlit as st


def sign_up(client, email: str, password: str):
    return client.auth.sign_up({"email": email, "password": password})


def sign_in(client, email: str, password: str):
    return client.auth.sign_in_with_password({"email": email, "password": password})


def sign_out(client) -> None:
    client.auth.sign_out()
    st.session_state.pop("user", None)


def render_login_gate(client, bug_tracker) -> bool:
    """Renders a login/sign-up form. Returns True once st.session_state['user'] is set."""
    if st.session_state.get("user"):
        return True

    st.title("🎓 SS Academic Coach")
    st.caption("Devam etmek için giriş yap veya hesap oluştur.")

    tab_login, tab_signup = st.tabs(["Giriş Yap", "Hesap Oluştur"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("E-posta", key="login_email")
            password = st.text_input("Şifre", type="password", key="login_password")
            submitted = st.form_submit_button("Giriş Yap")
        if submitted:
            try:
                result = sign_in(client, email, password)
                st.session_state["user"] = result.user
                st.rerun()
            except Exception as exc:
                bug_tracker.log(exc, context="login")
                st.error("Giriş başarısız. E-posta/şifreni kontrol et.")

    with tab_signup:
        with st.form("signup_form"):
            email = st.text_input("E-posta", key="signup_email")
            password = st.text_input("Şifre", type="password", key="signup_password")
            submitted = st.form_submit_button("Hesap Oluştur")
        if submitted:
            try:
                sign_up(client, email, password)
                st.success("Hesap oluşturuldu. E-postanı onayladıktan sonra giriş yapabilirsin.")
            except Exception as exc:
                bug_tracker.log(exc, context="signup")
                st.error("Hesap oluşturulamadı.")

    return False
