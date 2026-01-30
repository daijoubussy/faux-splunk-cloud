import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useTheme } from '../auth';
import Button from '@splunk/react-ui/Button';
import Text from '@splunk/react-ui/Text';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Message from '@splunk/react-ui/Message';
import Switch from '@splunk/react-ui/Switch';
import styled from 'styled-components';
import { variables, pick } from '@splunk/themes';

interface RegistrationData {
  company_name: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

interface RegistrationResponse {
  user: {
    username: string;
    user_id: string;
    status: string;
  };
  tenant: {
    tenant_id: string;
    name: string;
    slug: string;
  };
  login_url: string;
}

const PageContainer = styled.div`
  min-height: 100vh;
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorPage, light: variables.backgroundColorPage },
  })};
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 3rem 1.5rem;
`;

const Header = styled.header`
  position: absolute;
  top: 0;
  right: 0;
  padding: 1.5rem 2rem;
`;

const FormContainer = styled.div`
  max-width: 28rem;
  margin: 0 auto;
  width: 100%;
`;

const LogoSection = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 2rem;
`;

const LogoIcon = styled.div`
  width: 3rem;
  height: 3rem;
  background-color: ${variables.accentColorPositive};
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  font-size: 1.5rem;
  margin-bottom: 1rem;
`;

const Title = styled.h1`
  font-size: 1.875rem;
  font-weight: bold;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  text-align: center;
  margin-bottom: 0.5rem;
`;

const Subtitle = styled.p`
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  text-align: center;
  font-size: 0.875rem;
`;

const FormCard = styled.div`
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorDialog, light: variables.backgroundColorDialog },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  padding: 2rem;
  box-shadow: ${pick({
    prisma: { dark: variables.overlayShadow, light: variables.overlayShadow },
  })};
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
`;

const NameRow = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
`;

const HelperText = styled.p`
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  font-size: 0.75rem;
  margin-top: 0.25rem;
`;

const Divider = styled.div`
  display: flex;
  align-items: center;
  margin: 1.5rem 0;
`;

const DividerLine = styled.div`
  flex: 1;
  height: 1px;
  background-color: ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
`;

const DividerText = styled.span`
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  padding: 0 1rem;
  font-size: 0.875rem;
`;

const SignInLink = styled.a`
  display: block;
  width: 100%;
  text-align: center;
  padding: 0.75rem;
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.25rem;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background-color 0.2s;

  &:hover {
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
    })};
  }
`;

export default function Register() {
  const { theme, toggleTheme } = useTheme();
  const [formData, setFormData] = useState<RegistrationData>({
    company_name: '',
    email: '',
    password: '',
    first_name: '',
    last_name: '',
  });
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const registerMutation = useMutation({
    mutationFn: async (data: RegistrationData): Promise<RegistrationResponse> => {
      const response = await fetch('/api/v1/auth/saml/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Registration failed');
      }

      return response.json();
    },
    onSuccess: (data) => {
      window.location.href = data.login_url;
    },
    onError: (error: Error) => {
      setError(error.message);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (formData.password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    registerMutation.mutate(formData);
  };

  return (
    <PageContainer>
      <Header>
        <Switch
          selected={theme === 'light'}
          onClick={toggleTheme}
          appearance="toggle"
        >
          {theme === 'dark' ? 'Dark' : 'Light'}
        </Switch>
      </Header>

      <FormContainer>
        <LogoSection>
          <LogoIcon>S</LogoIcon>
          <Title>Create your account</Title>
          <Subtitle>Get started with Faux Splunk Cloud</Subtitle>
        </LogoSection>

        <FormCard>
          <Form onSubmit={handleSubmit}>
            {error && (
              <Message type="error">{error}</Message>
            )}

            <ControlGroup label="Company / Organization Name" labelPosition="top">
              <Text
                value={formData.company_name}
                onChange={(_, { value }) => setFormData({ ...formData, company_name: value })}
                placeholder="Acme Corporation"
                required
              />
              <HelperText>This will be used to create your tenant URL</HelperText>
            </ControlGroup>

            <NameRow>
              <ControlGroup label="First Name" labelPosition="top">
                <Text
                  value={formData.first_name}
                  onChange={(_, { value }) => setFormData({ ...formData, first_name: value })}
                />
              </ControlGroup>

              <ControlGroup label="Last Name" labelPosition="top">
                <Text
                  value={formData.last_name}
                  onChange={(_, { value }) => setFormData({ ...formData, last_name: value })}
                />
              </ControlGroup>
            </NameRow>

            <ControlGroup label="Email address" labelPosition="top">
              <Text
                type="email"
                value={formData.email}
                onChange={(_, { value }) => setFormData({ ...formData, email: value })}
                placeholder="you@example.com"
                required
              />
            </ControlGroup>

            <ControlGroup label="Password" labelPosition="top">
              <Text
                type="password"
                value={formData.password}
                onChange={(_, { value }) => setFormData({ ...formData, password: value })}
                placeholder="Minimum 8 characters"
                required
              />
            </ControlGroup>

            <ControlGroup label="Confirm Password" labelPosition="top">
              <Text
                type="password"
                value={confirmPassword}
                onChange={(_, { value }) => setConfirmPassword(value)}
                required
              />
            </ControlGroup>

            <Button
              appearance="primary"
              type="submit"
              disabled={registerMutation.isPending}
              label={registerMutation.isPending ? 'Creating account...' : 'Create Account'}
              style={{ width: '100%' }}
            />
          </Form>

          <Divider>
            <DividerLine />
            <DividerText>Already have an account?</DividerText>
            <DividerLine />
          </Divider>

          <SignInLink href="/">
            Sign in instead
          </SignInLink>
        </FormCard>
      </FormContainer>
    </PageContainer>
  );
}
