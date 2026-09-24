import type { ConfigContext, ExpoConfig } from 'expo/config';

export default ({ config }: ConfigContext): ExpoConfig => {
  const APP_VARIANT = process.env.APP_VARIANT;

  let name = 'Infrss';
  let bundleIdentifier = 'com.infrss.rss';
  let scheme = 'com.infrss.rss';
  let icon = './assets/app/icon.png';
  let adaptiveIconForeground = './assets/app/adaptive-icon.png';

  if (APP_VARIANT === 'development') {
    name = 'Infrss (Dev)';
    bundleIdentifier = 'com.infrss.rss.dev';
    scheme = 'com.infrss.rss.dev';
    icon = './assets/app/icon-dev.png';
    adaptiveIconForeground = './assets/app/adaptive-icon-dev.png';
  } else if (APP_VARIANT === 'preview') {
    name = 'Infrss (Preview)';
    bundleIdentifier = 'com.infrss.rss.preview';
    scheme = 'com.infrss.rss.preview';
    icon = './assets/app/icon-preview.png';
    adaptiveIconForeground = './assets/app/adaptive-icon-preview.png';
  }

  return {
    ...config,
    name,
    slug: 'infrss',
    version: '1.1.0',
    platforms: ['ios', 'android'],
    orientation: 'portrait',
    icon,
    userInterfaceStyle: 'automatic',
    backgroundColor: '#191919',
    scheme,
    updates: {
      url: 'https://u.expo.dev/e28b2485-c247-405c-829e-2b9c9c2e7733',
    },
    runtimeVersion: {
      policy: 'appVersion',
    },
    ios: {
      supportsTablet: false,
      bundleIdentifier,
      usesAppleSignIn: true,
      // Google Sign In requires reverse client ID scheme
      // The scheme is constructed from your Google OAuth iOS Client ID
      // Format: com.googleusercontent.apps.{CLIENT_ID_WITHOUT_SUFFIX}
      infoPlist: {
        ITSAppUsesNonExemptEncryption: false,
        CFBundleURLTypes: [
          {
            CFBundleURLSchemes: [
              scheme,
              ...(process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID
                ? [
                    `com.googleusercontent.apps.${process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID.replace(
                      '.apps.googleusercontent.com',
                      ''
                    )}`,
                  ]
                : []),
            ],
          },
        ],
        NSAppTransportSecurity: {
          NSAllowsArbitraryLoads: true,
        },
        NSLocalNetworkUsageDescription:
          'Infrss needs access to your local network to connect to self-hosted API servers.',
      },
    },
    android: {
      adaptiveIcon: {
        foregroundImage: adaptiveIconForeground,
        backgroundColor: '#343434',
      },
      package: bundleIdentifier,
    },
    web: {
      favicon: './assets/app/favicon.png',
    },
    developmentClient: {
      silentLaunch: true,
    },
    experiments: {
      tsconfigPaths: true,
    },
    plugins: [
      'expo-router',
      'expo-font',
      'expo-sqlite',
      'expo-localization',
      'expo-background-task',
      'expo-notifications',
      'expo-apple-authentication',
      [
        'expo-build-properties',
        {
          android: {
            usesCleartextTraffic: true,
          },
        },
      ],
      [
        'expo-web-browser',
        {
          experimentalLauncherActivity: true,
        },
      ],
      [
        '@sentry/react-native/expo',
        {
          url: 'https://sentry.io/',
          project: 'react-native',
          organization: 'infrss',
        },
      ],
      [
        'expo-splash-screen',
        {
          backgroundColor: '#191919',
          image: './assets/app/splash-icon.png',
          imageWidth: 200,
        },
      ],
    ],
    extra: {
      appVariant: APP_VARIANT || 'production',
      eas: {
        projectId: 'e28b2485-c247-405c-829e-2b9c9c2e7733',
      },
    },
  };
};
