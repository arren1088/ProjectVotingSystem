document.addEventListener("DOMContentLoaded", function () {
  const buttonPanel = document.querySelector('.button-panel');
  const confirmBtn = document.getElementById("confirmButton");
  let selectedGroups = [];

  if (!buttonPanel) {
    console.error('未找到 .button-panel 元素');
    return;
  }

  buttonPanel.addEventListener('click', function (e) {
    const button = e.target.closest('.show-details-btn');
    if (button) {
      const groupId = button.getAttribute('data-id');
      if (!groupId) return;

      const index = selectedGroups.indexOf(groupId);
      if (index !== -1) {
        selectedGroups.splice(index, 1);
        button.classList.remove("voted");
        button.innerHTML = `${button.getAttribute('data-lab-number')}<br>${groupId} <br> ${button.getAttribute('data-group-name')}`;
        button.style.background = '';
        button.style.boxShadow = '';
      } else {
        if (selectedGroups.length >= 3) {
          alert("最多只能選擇三組！");
          return;
        }
        selectedGroups.push(groupId);
        button.classList.add("voted");
        button.style.background = 'linear-gradient(135deg, #22c55e, #16a34a)';
        button.style.boxShadow = '0 6px 20px rgba(34, 197, 94, 0.3)';
      }

      updateConfirmButton();
    }
  });

  function updateConfirmButton() {
    confirmBtn.disabled = selectedGroups.length !== 3;
  }

  if (confirmBtn) {
    updateConfirmButton();

    confirmBtn.addEventListener("click", function (e) {
      e.preventDefault();

      if (selectedGroups.length !== 3) {
        alert("您必須選擇三個組別！");
        return;
      }

      fetch("/api/vote/confirm", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ selected_votes: selectedGroups }),
      })
        .then(response => response.json())
        .then(data => {
         if (data.success) {
              window.location.href = "/feedbacks";
          }else {
            alert(data.message || "確認投票失敗！");
          }
        })
        .catch(error => {
          console.error("確認投票錯誤:", error);
          alert("網路錯誤，請稍後再試。");
        });
    });
  }
});