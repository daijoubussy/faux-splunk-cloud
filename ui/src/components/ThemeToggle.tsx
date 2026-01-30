import { useTheme } from '../auth';
import Switch from '@splunk/react-ui/Switch';

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <Switch
      selected={theme === 'light'}
      onClick={toggleTheme}
      appearance="toggle"
    >
      {theme === 'dark' ? 'Dark' : 'Light'}
    </Switch>
  );
}

export default ThemeToggle;
