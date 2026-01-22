(() => {
  const showToast = (text, type = "success") => {
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

  if (window.DJANGO_MESSAGES?.length) {
    window.DJANGO_MESSAGES.forEach(msg => {
      const type = msg.level === "error" ? "error" : "success";
      showToast(msg.text, type);
    });
  }
})();
