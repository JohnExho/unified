    (() => {
      const profileForm = document.getElementById("profileForm");
      const successMsg = document.getElementById("successMessage");
      const firstNameInput = document.getElementById("firstName");
      const lastNameInput = document.getElementById("lastName");
      const avatarCircle = document.getElementById("avatarCircle");
      const avatarInput = document.getElementById("avatarInput");
      const modal = document.getElementById("addressModal");
      const openBtn = document.getElementById("openAddressModal");
      const closeBtn = document.getElementById("closeModal");
      const country2Input = document.getElementById("country2");
      const address2Fields = document.getElementById("address2Fields");

      // Profile Form submit
      /* profileForm?.addEventListener("submit", e => {
        e.preventDefault();
        successMsg.style.display = "block";
        window.scrollTo({ top:0, behavior:"smooth" });
        setTimeout(()=>successMsg.style.display="none",3000);
      });
        */
      // Cancel
      window.handleCancel = () => { if(confirm("Discard changes?")) location.reload(); }

      // Avatar initials
      const updateAvatar = () => {
        const initials = (firstNameInput.value.charAt(0)+lastNameInput.value.charAt(0)).toUpperCase();
        avatarCircle.textContent = initials || "JD";
      };
      firstNameInput?.addEventListener("input", updateAvatar);
      lastNameInput?.addEventListener("input", updateAvatar);

      // Avatar upload
      window.handleUploadPhoto = () => avatarInput?.click();
      avatarInput?.addEventListener("change", async () => {
        const file = avatarInput.files[0];
        if(!file) return;
        const formData = new FormData();
        formData.append("avatar", file);
        const res = await fetch("{% url 'core:upload_avatar' %}", {
          method:"POST",
          headers:{"X-CSRFToken":"{{ csrf_token }}"},
          body:formData
        });
        const data = await res.json();
        if(data.success){
          avatarCircle.style.backgroundImage = `url(${data.avatar_url})`;
          avatarCircle.textContent = "";
        }
      });

      // Avatar remove
      window.handleRemovePhoto = () => {
        if(!confirm("Remove profile photo?")) return;
        fetch("{% url 'core:remove_avatar' %}", {method:"POST", headers:{"X-CSRFToken":"{{ csrf_token }}"}})
          .then(()=>{ avatarCircle.style.backgroundImage=""; avatarCircle.textContent="JD"; });
      };

      // Address modal
      openBtn?.addEventListener("click", ()=>modal.classList.remove("hidden"));
      closeBtn?.addEventListener("click", ()=>modal.classList.add("hidden"));
      modal?.addEventListener("click", e=>{if(e.target===modal) modal.classList.add("hidden")});

      // Address 2 toggle
      country2Input?.addEventListener("input", ()=>{
        if(country2Input.value.trim()!=="") address2Fields.classList.remove("hidden");
        else {
          address2Fields.classList.add("hidden");
          address2Fields.querySelectorAll("input").forEach(i=>i.value="");
        }
      });

        const phoneInput = document.getElementById("phone");
        phoneInput.addEventListener("input", () => {
            phoneInput.value = phoneInput.value.replace(/\D/g, "");
        if (phoneInput.value.length > 20) {
            phoneInput.value = phoneInput.value.slice(0, 20);
           }
        });

    })();