# {{ candidate.name }}
**{{ headline }}**

## Summary
{{ summary }}

## Skills
{{ selected_skills | join(", ") }}

## Experience
{% for exp in selected_experiences %}
### {{ exp.role }} — {{ exp.company }} ({{ exp.start }}–{{ exp.end }})
{% for bullet in exp.bullets %}
- {{ bullet }}
{% endfor %}
{% endfor %}

## Projects
{% for proj in selected_projects %}
### {{ proj.name }}
{{ proj.description }}
{% endfor %}
