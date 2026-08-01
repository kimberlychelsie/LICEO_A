import sys, os

file_path = 'templates/student_billing_view.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# CSS to inject
css_to_add = '''
    /* ── Receipt UI (Glass Card) ── */
    .glass-card {
        background: white;
        border-radius: 20px;
        border: 1px solid var(--sd-border);
        box-shadow: 0 10px 30px rgba(0,0,0,0.02);
        overflow: hidden;
        margin-bottom: 32px;
    }

    .card-header {
        padding: 20px 24px;
        background: #fdfdfd;
        border-bottom: 1px solid var(--sd-border);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .card-header h2 {
        font-size: 1.1rem;
        font-weight: 800;
        color: var(--sd-primary);
        margin: 0;
    }

    .card-body { padding: 24px; }

    .receipt-item {
        display: flex;
        justify-content: space-between;
        padding: 12px 0;
        border-bottom: 1px solid #f1f5f9;
    }

    .receipt-item:last-child { border-bottom: none; }

    .item-name { font-weight: 700; font-size: 0.9rem; color: #334155; }
    .item-val { font-weight: 800; color: var(--sd-primary); }

    .status-badge {
        padding: 6px 14px;
        border-radius: 12px;
        font-size: 0.72rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .status-paid {
        background: #dcfce7;
        color: #166534;
        border: 1px solid #bbf7d0;
    }

    .status-unpaid {
        background: #fef3c7;
        color: #b45309;
        border: 1px solid #fde68a;
    }
'''

if '.receipt-item' not in content:
    content = content.replace('</style>', css_to_add + '\n</style>')

# JS to inject
js_to_add = '''
    function toggleFeeBreakdown() {
        const panel = document.getElementById('fee-breakdown-panel');
        const icon = document.getElementById('fee-toggle-icon');
        if (panel.style.maxHeight && panel.style.maxHeight !== '0px') {
            panel.style.maxHeight = '0px';
            icon.style.transform = 'rotate(0deg)';
        } else {
            panel.style.maxHeight = panel.scrollHeight + 100 + 'px';
            icon.style.transform = 'rotate(180deg)';
        }
    }
'''
if 'function toggleFeeBreakdown' not in content:
    content = content.replace('</script>', js_to_add + '\n</script>')

# HTML Replacement
start_marker = '            <!-- Bill Breakdown -->\\n            <div class=\"sd-card\">'
end_marker = '                </table>'

new_html = '''            <!-- Bill Breakdown -->
            <div class="glass-card">
                <div class="card-header" style="cursor: pointer; user-select: none; transition: background 0.2s;" onclick="toggleFeeBreakdown()">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <h2 style="margin: 0; display: flex; align-items: center; gap: 8px; font-weight: 800;">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" width="20" height="20">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            Fee Breakdown
                            <span id="fee-toggle-icon" style="display: inline-block; font-size: 1rem; color: #2563eb; transition: transform 0.3s ease; font-weight: 900; margin-left: 4px;">▼</span>
                        </h2>
                    </div>
                    {% if bill.status == 'paid' %}
                    <span class="status-badge status-paid">Paid</span>
                    {% else %}
                    <span class="status-badge status-unpaid">Pending</span>
                    {% endif %}
                </div>
                <div class="card-body">
                    <div style="display: flex; justify-content: space-between; align-items: center; cursor: pointer; user-select: none;" onclick="toggleFeeBreakdown()">
                        <span style="font-size: 0.85rem; font-weight: 700; color: #475569;">
                            Remaining Balance
                        </span>
                        <span style="font-size: 1.1rem; font-weight: 900; color: var(--sd-primary);">₱{{ "{:,.2f}".format(bill.balance) }}</span>
                    </div>

                    <div id="fee-breakdown-panel" style="max-height: 0; overflow: hidden; transition: max-height 0.35s ease-in-out; margin-top: 4px;">
                        <div style="padding-top: 12px; margin-top: 8px; border-top: 1px dashed #cbd5e1; max-height: 340px; overflow-y: auto; padding-right: 4px;">
                            <div class="receipt-item">
                                <span class="item-name">Tuition & Fees</span>
                                <span class="item-val">₱{{ "{:,.2f}".format(bill.tuition_fee) }}</span>
                            </div>
                            
                            {% if reservations %}
                                {% for res in reservations %}
                                <div class="receipt-item" style="flex-wrap: wrap;">
                                    <div style="display: flex; justify-content: space-between; width: 100%;">
                                        <span class="item-name" style="font-size: 0.8rem;">
                                            {{ res.item_names or 'Reservation' }}
                                            <span style="font-size:0.65rem; background:#e0e7ff; color:#3730a3; padding:2px 6px; border-radius:4px; font-weight:800; margin-left:6px;">Ref: #RES-{{ "%04d"|format(res.reservation_id) }}</span>
                                        </span>
                                        <span class="item-val">₱{{ "{:,.2f}".format(res.total_amount) }}</span>
                                    </div>
                                </div>
                                {% endfor %}
                            {% elif bill.books_fee > 0 %}
                                <div class="receipt-item"><span class="item-name">Books & Materials</span><span class="item-val">₱{{ "{:,.2f}".format(bill.books_fee) }}</span></div>
                            {% endif %}
                            
                            {% if uniform_orders %}
                                {% for uo in uniform_orders %}
                                <div class="receipt-item" style="flex-wrap: wrap;">
                                    <div style="display: flex; justify-content: space-between; width: 100%;">
                                        <span class="item-name" style="font-size: 0.8rem;">
                                            {{ uo.item_names }}
                                            <span style="font-size:0.65rem; background:#ffedd5; color:#c2410c; padding:2px 6px; border-radius:4px; font-weight:800; margin-left:6px;">{{ uo.order_number }} · {{ uo.order_status }}</span>
                                        </span>
                                        <span class="item-val">₱{{ "{:,.2f}".format(uo.total_amount) }}</span>
                                    </div>
                                    {% if uo.pieces and uo.pieces|length > 0 %}
                                    <div style="width: 100%; margin-top: 6px; padding: 6px 10px; background: #f8fafc; border-radius: 8px; font-size: 0.72rem; border: 1px solid #e2e8f0;">
                                        {% for p in uo.pieces %}
                                        <div style="display: flex; justify-content: space-between; padding: 2px 0; color: #475569;">
                                            <span>• {{ p.item_name }} {% if p.size_label %}({{ p.size_label }}){% endif %} {% if p.quantity > 1 %}x{{ p.quantity }}{% endif %}</span>
                                            <span style="font-weight: 700;">₱{{ "{:,.2f}".format(p.line_total) }}</span>
                                        </div>
                                        {% endfor %}
                                    </div>
                                    {% endif %}
                                </div>
                                {% endfor %}
                            {% elif bill.uniform_fee > 0 %}
                                <div class="receipt-item"><span class="item-name">Uniforms</span><span class="item-val">₱{{ "{:,.2f}".format(bill.uniform_fee) }}</span></div>
                            {% endif %}
                            
                            {% if bill.other_fees > 0 %}
                                <div class="receipt-item"><span class="item-name">Miscellaneous / Other Fees</span><span class="item-val">₱{{ "{:,.2f}".format(bill.other_fees) }}</span></div>
                            {% endif %}
                            
                            <div class="receipt-item" style="border-top: 2px solid #cbd5e1; margin-top: 8px;">
                                <span class="item-name" style="font-size: 1rem;">Total Assessment</span>
                                <span class="item-val" style="font-size: 1.2rem;">₱{{ "{:,.2f}".format(bill.total_amount) }}</span>
                            </div>
                        </div>
                    </div><!-- END PANEL -->'''

start_idx = content.find('            <!-- Bill Breakdown -->')
end_idx = content.find('                </table>', start_idx)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_html + content[end_idx + len('                </table>'):]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS')
else:
    print('COULD NOT FIND BLOCK TO REPLACE')
    print('start_idx:', start_idx, 'end_idx:', end_idx)
