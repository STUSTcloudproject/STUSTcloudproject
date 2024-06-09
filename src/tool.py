def update_profile(color_profiles, depth_profiles):
    """
    更新配置文件的組合框以匹配相應的配置文件。

    參數:
    color_profiles (list): 顏色配置文件列表
    depth_profiles (list): 深度配置文件列表

    回傳:
    tuple: 包含匹配的深度配置文件和選定的顏色配置文件的元組
    """
    # 匹配深度配置文件，條件是顏色配置文件中存在相同的寬度、高度和幀率
    matched_depth_profiles = [
        profile for profile in depth_profiles
        if any((profile[0], profile[1], profile[2]) == (cp[0], cp[1], cp[2]) for cp in color_profiles)
    ]

    # 匹配顏色配置文件，條件是深度配置文件中存在相同的寬度、高度和幀率
    matched_color_profiles = [
        cp for cp in color_profiles
        if any((cp[0], cp[1], cp[2]) == (profile[0], profile[1], profile[2]) for profile in depth_profiles)
    ]

    # 選擇第一個格式為 rgb8 的顏色配置文件
    selected_color_profiles = []
    for dp in matched_depth_profiles:
        for cp in matched_color_profiles:
            if (cp[0], cp[1], cp[2]) == (dp[0], dp[1], dp[2]) and cp[3].name == 'rgb8':
                selected_color_profiles.append(cp)
                break

    # 回傳匹配的深度配置文件和選定的顏色配置文件
    return matched_depth_profiles, selected_color_profiles
