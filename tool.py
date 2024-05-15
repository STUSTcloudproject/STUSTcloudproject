def update_profile(color_profiles, depth_profiles):
        """Updates the profile combobox with matching profiles."""
        matched_depth_profiles = [
            profile for profile in depth_profiles
            if any((profile[0], profile[1], profile[2]) == (cp[0], cp[1], cp[2]) for cp in color_profiles)
        ]

        matched_color_profiles = [
            cp for cp in color_profiles
            if any((cp[0], cp[1], cp[2]) == (profile[0], profile[1], profile[2]) for profile in depth_profiles)
        ]

        # 选择第一个格式为 format.rgb8 的颜色配置文件
        selected_color_profiles = []
        for dp in matched_depth_profiles:
            for cp in matched_color_profiles:
                if (cp[0], cp[1], cp[2]) == (dp[0], dp[1], dp[2]) and cp[3].name == 'rgb8':
                    selected_color_profiles.append(cp)
                    break

        return matched_depth_profiles, selected_color_profiles