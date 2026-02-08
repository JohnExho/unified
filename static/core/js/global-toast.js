(() => {
  const messages = window.DJANGO_MESSAGES || [];
  if (!messages.length) return;

  const showToast = (text, type = "success") => {
    if (!window.Swal) return;
    Swal.fire({
      toast: true,
      position: "top-end",
      icon: type,
      title: text,
      showConfirmButton: false,
      timer: 3000,
      timerProgressBar: true,
      background: "#fff",
      iconColor: type === "error" ? "#f56565" : "#48bb78",
      customClass: { popup: "shadow-lg rounded-md p-3" }
    });
  };

  const ensureSwal = () =>
    new Promise((resolve, reject) => {
      if (window.Swal) return resolve();
      const script = document.createElement("script");
      script.src = "https://cdn.jsdelivr.net/npm/sweetalert2@11";
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("SweetAlert2 failed to load"));
      document.head.appendChild(script);
    });

  ensureSwal()
    .then(() => {
      messages.forEach(msg => {
        const type = msg.level === "error" ? "error" : "success";
        showToast(msg.text, type);
      });
    })
    .catch(() => {
      messages.forEach(msg => {
        alert(msg.text);
      });
    });
})();
