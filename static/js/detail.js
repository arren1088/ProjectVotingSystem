document.addEventListener("DOMContentLoaded", function () {
  const buttonPanel = document.querySelector('.button-panel');
  const detailPanel = document.querySelector('.detail-panel');
  let votes = userVotes.length || 0;

  if (!buttonPanel || !detailPanel) {
    console.error('未找到 .button-panel 或 .detail-panel 元素');
    return;
  }

  // 初始化：加上已投票樣式與文字，但不鎖按鈕
  userVotes.forEach(groupId => {
    const voteBtn = document.querySelector(`.vote-btn[data-id="${groupId}"]`);
    if (voteBtn) {
      voteBtn.textContent = "已投票";
      voteBtn.classList.add("voted");
    }
  });

  // 左側：顯示詳情按鈕點擊
  buttonPanel.addEventListener('click', function (e) {
    const button = e.target.closest('.show-details-btn');
    if (button) {
      const groupId = button.getAttribute('data-id');
      showDetails(groupId);
    }
  });

  // 右側：投票按鈕點擊
  detailPanel.addEventListener('click', function (e) {
    const voteButton = e.target.closest('.vote-btn');
    if (voteButton) {
      const groupId = voteButton.getAttribute('data-id');
      fetch("/api/toggle_vote", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ group_id: groupId }),
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          // 更新投票按鈕的文字與樣式
          voteButton.textContent = data.voted ? "已投票" : "投票";
          voteButton.classList.toggle("voted", data.voted);

          // 更新投票數與確認按鈕顯示
          votes = data.vote_count;
          const confirmBtn = document.getElementById("confirmButton"); // 確保選擇正確的按鈕
          if (confirmBtn) {
            confirmBtn.style.display = votes === 3 ? "block" : "none"; // 只有當投票數為3時顯示
          }
        } else {
          alert(data.message || '操作失敗！請稍後再試。');
        }
      })
      .catch(error => {
        console.error("投票錯誤:", error);
      });
    }
  });

  // 顯示指定組別的詳細資料
  function showDetails(groupId) {
    const detailDiv = document.getElementById(`detail-${groupId}`);
    const allDetails = document.querySelectorAll('.detail');
    const allButtons = document.querySelectorAll('.show-details-btn');

    if (!detailDiv) {
      console.error(`未找到 detail-${groupId}`);
      return;
    }

    // 隱藏其他細節、取消按鈕高亮
    allDetails.forEach(d => d.style.display = 'none');
    allButtons.forEach(btn => btn.classList.remove('active'));

    // 顯示當前選擇的
    detailDiv.style.display = 'flex';
    const currentBtn = document.querySelector(`.show-details-btn[data-id="${groupId}"]`);
    if (currentBtn) {
      currentBtn.classList.add('active');
    }

    // 在手機版中，顯示詳細資訊
    if (window.innerWidth <= 768) {
      detailDiv.classList.add('expand');
    }
  }

  // 點擊確認後跳轉到成功頁面
  const confirmBtn = document.getElementById("confirmButton"); // 確保選擇正確的按鈕
  if (confirmBtn) {
    confirmBtn.addEventListener("click", function () {
      fetch("/api/vote/confirm", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          window.location.href = "/succeed"; // 跳轉至成功頁面
        } else {
          alert(data.message); // 顯示錯誤訊息
        }
      })
      .catch(error => {
        console.error('投票錯誤:', error);
      });
    });
  }

  // 根據當前投票數顯示確認按鈕
  if (confirmBtn) {
    confirmBtn.style.display = votes === 3 ? "block" : "none"; // 顯示或隱藏確認按鈕
  }
});