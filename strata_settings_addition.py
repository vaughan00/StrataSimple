#
# Strata Settings Routes
#

@app.route('/settings', methods=['GET', 'POST'])
def strata_settings():
    """Page for managing strata-wide settings."""
    # Get or create settings
    settings = StrataSettings.get_settings()
    
    if request.method == 'POST':
        # Update settings from form
        settings.strata_name = request.form.get('strata_name')
        settings.address = request.form.get('address')
        settings.admin_email = request.form.get('admin_email')
        settings.bank_account_name = request.form.get('bank_account_name')
        settings.bank_bsb = request.form.get('bank_bsb')
        settings.bank_account_number = request.form.get('bank_account_number')
        
        db.session.commit()
        
        # Log activity
        log_activity(
            event_type='settings_updated',
            description='Strata settings updated',
            related_type='StrataSettings',
            related_id=settings.id
        )
        
        flash("Strata settings updated successfully!", "success")
        return redirect(url_for('strata_settings'))
    
    return render_template('strata_settings.html', settings=settings)


# Context processor to make strata settings available in all templates
@app.context_processor
def inject_strata_settings():
    """Make strata settings available in all templates."""
    return {"strata_settings": StrataSettings.get_settings()}