<#macro registrationLayout bodyClass="" displayInfo=false displayMessage=true displayRequiredFields=false>
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="robots" content="noindex, nofollow">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <#if properties.meta?has_content>
        <#list properties.meta?split(' ') as meta>
            <meta name="${meta?split('==')[0]}" content="${meta?split('==')[1]}"/>
        </#list>
    </#if>

    <title>${msg("loginTitle",(realm.displayName!''))}</title>
    <link rel="icon" href="${url.resourcesPath}/img/favicon.ico" />

    <#if properties.stylesCommon?has_content>
        <#list properties.stylesCommon?split(' ') as style>
            <link href="${url.resourcesCommonPath}/${style}" rel="stylesheet" />
        </#list>
    </#if>
    <#if properties.styles?has_content>
        <#list properties.styles?split(' ') as style>
            <link href="${url.resourcesPath}/${style}" rel="stylesheet" />
        </#list>
    </#if>

    <style>
        /* Inline critical styles for fast initial render */
        body {
            background-color: #0D0D0D;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 1rem;
            box-sizing: border-box;
        }
    </style>
</head>

<body class="login-pf ${bodyClass}">
    <div id="kc-container">
        <div id="kc-container-wrapper">

            <#-- Logo -->
            <div id="kc-logo-wrapper">
                <div class="kc-logo-text"></div>
            </div>

            <#-- Login Card -->
            <div class="card-pf">
                <#-- Page Title -->
                <header id="kc-header" class="login-pf-header">
                    <div id="kc-header-wrapper">
                        <#nested "header">
                    </div>
                </header>

                <div id="kc-content">
                    <div id="kc-content-wrapper">

                        <#-- Display message if exists -->
                        <#if displayMessage && message?has_content && (message.type != 'warning' || !isAppInitiatedAction??)>
                            <div class="alert alert-${message.type}">
                                <#if message.type = 'success'><span class="alert-icon">✓</span></#if>
                                <#if message.type = 'warning'><span class="alert-icon">⚠</span></#if>
                                <#if message.type = 'error'><span class="alert-icon">✕</span></#if>
                                <#if message.type = 'info'><span class="alert-icon">ℹ</span></#if>
                                <span class="kc-feedback-text">${kcSanitize(message.summary)?no_esc}</span>
                            </div>
                        </#if>

                        <#-- Form -->
                        <#nested "form">

                        <#-- Social Providers -->
                        <#if auth?has_content && auth.showTryAnotherWayLink()>
                            <form id="kc-select-try-another-way-form" action="${url.loginAction}" method="post">
                                <div class="form-group">
                                    <input type="hidden" name="tryAnotherWay" value="on"/>
                                    <a href="#" id="try-another-way"
                                       onclick="document.forms['kc-select-try-another-way-form'].submit();return false;">${msg("doTryAnotherWay")}</a>
                                </div>
                            </form>
                        </#if>

                        <#nested "socialProviders">

                        <#-- Info Section -->
                        <#if displayInfo>
                            <div id="kc-info">
                                <div id="kc-info-wrapper">
                                    <#nested "info">
                                </div>
                            </div>
                        </#if>
                    </div>
                </div>
            </div>

            <#-- Footer -->
            <div id="kc-footer">
                <p style="text-align: center; color: #5C5C5C; font-size: 0.75rem; margin-top: 2rem;">
                    Faux Splunk Cloud - Ephemeral Splunk Environments
                </p>
            </div>
        </div>
    </div>
</body>
</html>
</#macro>
