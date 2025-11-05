window.onload = function() {
    fetch("/api/admin/feedbacks")
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const tbody = document.querySelector("#feedback_table tbody");
            tbody.innerHTML = "";

            if (data.success) {
                const feedbacks = data.feedbacks;
                if (feedbacks.length === 0) {
                    const row = document.createElement("tr");
                    row.innerHTML = `<td colspan="6" style="text-align: center;">${data.message || '目前沒有回饋資料'}</td>`;
                    tbody.appendChild(row);
                    return;
                }

                feedbacks.forEach(feedback => {
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>${feedback.studentId || 'N/A'}</td>
                        <td>${feedback.studentName || 'N/A'}</td>
                        <td>${feedback.groupName || 'N/A'}</td>
                        <td>${feedback.feedbackDate || 'N/A'}</td>
                        <td>${feedback.feedbackTime || 'N/A'}</td>
                        <td class="feedback-content">${feedback.feedback || 'N/A'}</td>
                    `;
                    tbody.appendChild(row);
                });
            } else {
                alert("獲取回饋資料失敗：" + (data.message || '未知錯誤'));
                const row = document.createElement("tr");
                row.innerHTML = `<td colspan="6" style="text-align: center;">無法載入回饋資料</td>`;
                tbody.appendChild(row);
            }
        })
        .catch(error => {
            alert("發生錯誤，請稍後再試！");
            console.error("Error:", error);
            const tbody = document.querySelector("#feedback_table tbody");
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center;">無法載入回饋資料</td></tr>`;
        });
};