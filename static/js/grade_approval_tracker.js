(function () {
    const modal = document.getElementById('approvalHistoryModal');
    const openButton = document.getElementById('openApprovalHistory');
    const closeButton = document.getElementById('closeApprovalHistory');
    if (!modal || !openButton || !closeButton) return;
    let returnFocus = null;
    function closeHistory() {
        modal.classList.remove('open');
        modal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('approval-modal-open');
        if (returnFocus) returnFocus.focus();
    }
    openButton.addEventListener('click', function () {
        returnFocus = document.activeElement;
        modal.classList.add('open');
        modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('approval-modal-open');
        closeButton.focus();
    });
    closeButton.addEventListener('click', closeHistory);
    modal.addEventListener('click', function (event) {
        if (event.target === modal) closeHistory();
    });
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && modal.classList.contains('open')) closeHistory();
    });
})();
