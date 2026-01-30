import { useSAML, useTheme } from '../auth';
import Button from '@splunk/react-ui/Button';
import Switch from '@splunk/react-ui/Switch';
import {
  ServerIcon,
  ShieldExclamationIcon,
  ClockIcon,
  BeakerIcon,
} from '@heroicons/react/24/outline';
import styled from 'styled-components';
import { variables, pick } from '@splunk/themes';

const PageContainer = styled.div`
  min-height: 100vh;
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorPage, light: variables.backgroundColorPage },
  })};
  display: flex;
  flex-direction: column;
`;

const Header = styled.header`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 50;
  padding: 1.5rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const Logo = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const LogoIcon = styled.div`
  width: 2.5rem;
  height: 2.5rem;
  background-color: ${variables.accentColorPositive};
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  font-size: 1.25rem;
`;

const LogoText = styled.span`
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  font-weight: 600;
  font-size: 1.25rem;
`;

const HeroSection = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6rem 1.5rem 3rem;
  text-align: center;
`;

const HeroTitle = styled.h1`
  font-size: 3rem;
  font-weight: bold;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin-bottom: 1.5rem;
  max-width: 48rem;

  @media (max-width: 640px) {
    font-size: 2rem;
  }
`;

const HeroSubtitle = styled.p`
  font-size: 1.125rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  margin-bottom: 2.5rem;
  max-width: 32rem;
  line-height: 1.75;
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
`;

const FeaturesSection = styled.div`
  padding: 3rem 1.5rem 4rem;
  max-width: 64rem;
  margin: 0 auto;
`;

const FeaturesHeading = styled.div`
  text-align: center;
  margin-bottom: 3rem;
`;

const FeaturesSubtitle = styled.p`
  color: ${variables.accentColorPositive};
  font-weight: 600;
  margin-bottom: 0.5rem;
`;

const FeaturesTitle = styled.h2`
  font-size: 1.875rem;
  font-weight: bold;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin-bottom: 1rem;
`;

const FeaturesDescription = styled.p`
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  max-width: 32rem;
  margin: 0 auto;
`;

const FeaturesGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 2rem;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;

const FeatureCard = styled.div`
  display: flex;
  gap: 1rem;
`;

const FeatureIconWrapper = styled.div`
  flex-shrink: 0;
  width: 2.5rem;
  height: 2.5rem;
  background-color: ${variables.accentColorPositive};
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
`;

const FeatureContent = styled.div``;

const FeatureName = styled.h3`
  font-weight: 600;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin-bottom: 0.5rem;
`;

const FeatureDescription = styled.p`
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  font-size: 0.875rem;
  line-height: 1.5;
`;

const Footer = styled.footer`
  border-top: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  padding: 1.5rem;
  text-align: center;
`;

const FooterText = styled.p`
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  font-size: 0.875rem;
`;

const AdminLink = styled.a`
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  font-size: 0.875rem;
  text-decoration: none;
  transition: color 0.2s;

  &:hover {
    color: ${variables.accentColorPositive};
  }
`;

const features = [
  {
    name: 'Ephemeral Splunk Instances',
    description: 'Spin up Victoria-like Splunk environments on demand. Perfect for development, testing, and training.',
    icon: ServerIcon,
  },
  {
    name: 'Attack Simulation',
    description: 'Simulate adversarial attacks from script kiddies to nation-state APTs. Generate realistic security logs.',
    icon: ShieldExclamationIcon,
  },
  {
    name: 'Time-Limited Environments',
    description: 'Instances automatically clean up after their TTL expires. No manual cleanup needed.',
    icon: ClockIcon,
  },
  {
    name: 'Security Training',
    description: 'Practice threat hunting and incident response with realistic attack scenarios based on MITRE ATT&CK.',
    icon: BeakerIcon,
  },
];

export default function Login() {
  const { login } = useSAML();
  const { theme, toggleTheme } = useTheme();

  return (
    <PageContainer>
      <Header>
        <Logo>
          <LogoIcon>S</LogoIcon>
          <LogoText>Faux Splunk Cloud</LogoText>
        </Logo>
        <Switch
          selected={theme === 'light'}
          onClick={toggleTheme}
          appearance="toggle"
        >
          {theme === 'dark' ? 'Dark' : 'Light'}
        </Switch>
      </Header>

      <HeroSection>
        <HeroTitle>
          Ephemeral Splunk Cloud Environments
        </HeroTitle>
        <HeroSubtitle>
          Create on-demand Splunk instances for development, testing, and security training.
          Run realistic attack simulations and practice threat hunting in a safe environment.
        </HeroSubtitle>
        <ButtonGroup>
          <Button
            appearance="primary"
            onClick={() => login()}
            label="Sign In"
          />
          <Button
            appearance="secondary"
            to="/register"
            label="Register"
          />
        </ButtonGroup>
        <AdminLink href="/admin">
          Admin Portal
        </AdminLink>
      </HeroSection>

      <FeaturesSection>
        <FeaturesHeading>
          <FeaturesSubtitle>Security Training Platform</FeaturesSubtitle>
          <FeaturesTitle>Everything you need for security training</FeaturesTitle>
          <FeaturesDescription>
            Faux Splunk Cloud provides ephemeral Splunk environments with realistic attack simulations
            for hands-on security training.
          </FeaturesDescription>
        </FeaturesHeading>

        <FeaturesGrid>
          {features.map((feature) => (
            <FeatureCard key={feature.name}>
              <FeatureIconWrapper>
                <feature.icon style={{ width: '1.5rem', height: '1.5rem', color: 'white' }} />
              </FeatureIconWrapper>
              <FeatureContent>
                <FeatureName>{feature.name}</FeatureName>
                <FeatureDescription>{feature.description}</FeatureDescription>
              </FeatureContent>
            </FeatureCard>
          ))}
        </FeaturesGrid>
      </FeaturesSection>

      <Footer>
        <FooterText>
          Faux Splunk Cloud - Ephemeral Splunk Environments for Security Training
        </FooterText>
      </Footer>
    </PageContainer>
  );
}
