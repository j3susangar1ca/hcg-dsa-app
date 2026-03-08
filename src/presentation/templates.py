from string import Template

RESULTADO_TEMPLATE = Template("""
<div style='line-height: 1.6; font-family: "Segoe UI", sans-serif;'>
    <div style="margin-bottom: 12px;">
        <span style="color: #6B7280; font-size: 12px;">🏢 REMITENTE</span><br>
        <b style="color: #111827; font-size: 14px;">$remitente</b>
    </div>
    <div style="margin-bottom: 12px;">
        <span style="color: #6B7280; font-size: 12px;">📝 ASUNTO</span><br>
        <b style="color: #111827; font-size: 14px;">$asunto</b>
    </div>
    <div>
        <span style="color: #6B7280; font-size: 12px;">🎯 ACCIÓN SUGERIDA</span><br>
        <span style="color: #2563EB; font-weight: bold; font-size: 13px; 
                     background: #EFF6FF; padding: 4px 8px; border-radius: 4px;">
            $estatus
        </span>
    </div>
</div>
""")
