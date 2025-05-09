document.addEventListener("DOMContentLoaded", function () {
  const buttonPanel = document.querySelector('.button-panel');
  const detailPanel = document.querySelector('.detail-panel');
  let votesSelected = userVotes.length || 0; // 初始化為已投票數量

  if (!buttonPanel || !detailPanel) {
    console.error('未找到 .button-panel 或 .detail-panel 元素');
    return;
  }

  // 初始化已投票按鈕的樣式
  userVotes.forEach(groupId => {
    const button = document.querySelector(`.show-details-btn[data-id="${groupId}"]`);
    if (button) {
      button.textContent = "已投票";
      button.classList.add("voted");
    }
  });

  // 點擊事件監聽器
  buttonPanel.addEventListener('click', function (e) {
    const button = e.target.closest('.show-details-btn');
    if (button) {
      const groupId = button.getAttribute('data-id'); // 修正為 data-id
      if (!groupId) {
        console.error('未找到 data-id 屬性');
        return;
      }
      showDetails(groupId);
      toggleVote(groupId, button);
    }
  });

  function showDetails(groupId) {
    const detailDiv = document.getElementById(`detail-${groupId}`);
    const allDetails = document.querySelectorAll('.detail');
    const allButtons = document.querySelectorAll('.show-details-btn');

    if (!detailDiv) {
      console.error(`未找到 detail-${groupId}`);
      return;
    }

    allDetails.forEach(d => d.style.display = 'none');
    allButtons.forEach(btn => btn.classList.remove('active'));

    detailDiv.style.display = 'flex';
    const currentBtn = document.querySelector(`.show-details-btn[data-id="${groupId}"]`);
    if (currentBtn) {
      currentBtn.classList.add('active');
    }

    if (window.innerWidth <= 768) {
      detailDiv.classList.add('expand');
    }
  }

  function toggleVote(groupId, button) {
    fetch("/api/toggle_vote", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ group_id: groupId }),
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP 錯誤: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.success) {
        const wasVoted = userVotes.includes(groupId);
        if (!wasVoted) {
          // 新增投票
          button.classList.add("voted");
          button.style.background = 'linear-gradient(135deg, #22c55e, #16a34a)';
          button.style.boxShadow = '0 6px 20px rgba(34, 197, 94, 0.3)';
          userVotes.push(groupId);
          votesSelected += 1;
        } else {
          // 取消投票
          button.textContent = groupId; // 恢復為組別 ID
          button.classList.remove("voted");
          button.style.background = ''; // 清除綠色漸層
          button.style.boxShadow = ''; // 清除陰影
          const index = userVotes.indexOf(groupId);
          if (index !== -1) {
            userVotes.splice(index, 1);
          }
          votesSelected -= 1;
        }
        updateVoteStatus();
      } else {
        alert(data.message || '操作失敗！請稍後再試。');
      }
    })
    .catch(error => {
      console.error("投票錯誤:", error);
      alert('網路錯誤，請稍後再試。');
    });
  }

  const confirmBtn = document.getElementById("confirmButton");
  if (confirmBtn) {
    confirmBtn.addEventListener("click", function () {
      fetch("/api/vote/confirm", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
      })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP 錯誤: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        if (data.success) {
          window.location.href = "/succeed";
        } else {
          alert(data.message || '確認投票失敗！');
        }
      })
      .catch(error => {
        console.error('確認投票錯誤:', error);
        alert('網路錯誤，請稍後再試。');
      });
    });
  }

  function updateVoteStatus() {
    if (votesSelected >= 3) {
      confirmBtn.disabled = false;
      confirmBtn.style.display = "block";
    } else {
      confirmBtn.disabled = true;
      confirmBtn.style.display = "none";
    }
  }

  if (confirmBtn) {
    updateVoteStatus(); // 初始化確認按鈕狀態
  }
});